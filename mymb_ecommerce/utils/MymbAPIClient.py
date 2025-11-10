import base64
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta

import frappe
import requests
from frappe import _
from frappe.utils import cint, cstr, get_datetime
from pytz import timezone

from mymb_ecommerce.mymb_b2c.constants import SETTINGS_DOCTYPE
from mymb_ecommerce.mymb_b2c.utils import create_mymb_b2c_log
from frappe.utils.password import get_decrypted_password
from datetime import datetime
from requests.exceptions import ReadTimeout, ConnectTimeout, HTTPError, ConnectionError
from mymb_ecommerce.utils.CircuitBreaker import CircuitBreaker


JsonDict = Dict[str, Any]


class MymbAPIClient:
	"""Wrapper around MymbAPIClient REST API

	API docs: https://documentation.mymb_b2c.com/
	"""

	def __init__(
		self, 
		url: Optional[str] = None, 
		access_token: Optional[str] = None,
		api_username: Optional[str] = None,
		api_password: Optional[str] = None,
		settings_doctype: Optional[str] = SETTINGS_DOCTYPE,
		
	):
		self.settings = frappe.get_doc(settings_doctype)
		self.base_url = url or self.settings.mymb_base_api_url
		self.access_token = access_token

		# Set the API username and password either from the parameters or from the settings
		self.api_username = api_username or self.settings.mymb_api_username
		self.api_password = api_password or get_decrypted_password(settings_doctype, self.settings.name, "mymb_api_password")

		self.__initialize_auth()

		# Initialize circuit breaker for this API endpoint
		# Prevents cascading failures when external B2B API is down
		self.circuit_breaker = CircuitBreaker(
			name=f"mymb_api_{self.base_url}",
			failure_threshold=3,  # Open after 3 failures
			timeout_seconds=30,   # Try again after 30 seconds
			half_open_max_calls=2  # Test with 2 calls before fully reopening
		)

	def __initialize_auth(self):
		"""Initialize and setup authentication details"""
		encoded_credentials = base64.b64encode(f'{self.api_username}:{self.api_password}'.encode('utf-8')).decode('utf-8')
		self._auth_headers = {"Authorization": f"Basic {encoded_credentials}"}

	def _send_rate_limited_email(
		self,
		error_type: str,
		endpoint: str,
		subject: str,
		message: str,
		recipients: Optional[List[str]] = None,
		rate_limit_minutes: int = 30
	):
		"""
		Send email notification with rate limiting to avoid spam.
		Only sends one email per error_type+endpoint combination within rate_limit_minutes.

		Args:
			error_type: Type of error (timeout, connection_error, server_error, etc.)
			endpoint: API endpoint that failed
			subject: Email subject
			message: Email message
			recipients: List of email recipients (default: admin and support)
			rate_limit_minutes: Minutes to wait before sending another email for same error (default: 30)
		"""
		if recipients is None:
			recipients = ["admin@crowdechain.com", "daniele.ammazzini@timegroup.it", "giovanni.abbatino@timegroup.it"]


		# Create a unique cache key for this error type and endpoint
		cache_key = f"mymb_api_email_{error_type}_{endpoint.replace('/', '_')}"

		# Check if we've already sent an email recently
		cache = frappe.cache()
		last_sent = cache.get(cache_key)

		if last_sent:
			# Email was already sent recently, skip
			frappe.log_error(
				message=f"Email notification suppressed (rate limited). Last sent: {last_sent}",
				title=f"Email Rate Limited - {error_type}"
			)
			return

		# Send the email
		try:
			frappe.sendmail(
				recipients=recipients,
				subject=subject,
				message=message,
				sender=frappe.db.get_single_value("Email Account", "email_id")
			)
			# Mark in cache that we sent this email
			cache.setex(cache_key, rate_limit_minutes * 60, str(datetime.now()))
		except Exception as email_error:
			frappe.log_error(
				message=f"Failed to send {error_type} notification email: {str(email_error)}",
				title="Sendmail Failure"
			)

	
	def request(
		self,
		endpoint: str,
		method: str = "POST",
		headers: Optional[JsonDict] = None,
		body: Optional[JsonDict] = None,
		params: Optional[JsonDict] = None,
		files: Optional[JsonDict] = None,
		log_error=True,
	) -> Tuple[JsonDict, bool]:

		if headers is None:
			headers = {}

		headers.update(self._auth_headers)

		url = self.base_url + endpoint

		try:
			# Wrap API call with circuit breaker to fail fast if service is down
			# This prevents blocking workers when B2B API is unavailable
			def _make_request():
				response = requests.request(
					url=url, method=method, headers=headers, json=body, params=params, files=files, timeout=(3, 30)
				)
				# mymb_b2c gives useful info in response text, show it in error logs
				response.reason = cstr(response.reason) + cstr(response.text)
				response.raise_for_status()
				return response

			response = self.circuit_breaker.call(_make_request)
		except (ReadTimeout, ConnectTimeout) as timeout_error:
			error_message = f"Timeout occurred while accessing {url}: {str(timeout_error)}"
			frappe.log_error(message=error_message, title=f"Request Timeout - {endpoint}")

			# Avoid sending email if the endpoint is /GetEsposizioneAggiornataB2B
			if "/GetEsposizioneAggiornataB2B" not in endpoint:
				self._send_rate_limited_email(
					error_type="timeout",
					endpoint=endpoint,
					subject=f"[TIMEOUT ERROR] API call failed at {endpoint}",
					message=error_message
				)

			return None, False

		except HTTPError as http_err:
			if 400 <= http_err.response.status_code < 500:
				# Ignore client-side errors (e.g., 401, 403, 404)
				frappe.log_error(
					message=f"Client error at {url}: {str(http_err)}",
					title=f"Client Error - {endpoint}"
				)
			else:
				# Server-side errors
				error_message = f"Server error while {url}: {str(http_err)}"
				frappe.log_error(message=error_message, title=f"Server Error - {endpoint}")
				self._send_rate_limited_email(
					error_type="server_error",
					endpoint=endpoint,
					subject=f"[SERVER ERROR] Request failed at {endpoint}",
					message=error_message,
					recipients=["admin@crowdechain.com"]
				)
			return None, False

		except ConnectionError as conn_err:
			error_message = f"Connection failed - endpoint unreachable at {url}: {str(conn_err)}"
			frappe.log_error(message=error_message, title=f"Connection Error - {endpoint}")

			# Send email notification for connection failures
			self._send_rate_limited_email(
				error_type="connection_error",
				endpoint=endpoint,
				subject=f"[CONNECTION ERROR] API endpoint unreachable: {endpoint}",
				message=error_message
			)

			return None, False

		except Exception as e:
			error_message = f"An error occurred while {url}: {str(e)}"
			frappe.log_error(message=error_message, title=f"Request Error - {endpoint}")
			return None, False

		if method == "GET" and "application/json" not in response.headers.get("content-type"):
			return response.content, True

		# Parse the response content
		data = response.json()

		# Get the key of the main result object. This assumes that your response 
		# always has a single key at the top level.
		result_key = list(data.keys())[0] if data and isinstance(data, dict) else None
		result_data = data.get(result_key, {})

		# Check if ReturnCode is not 0 in the response and log the error
		if 'ReturnCode' in result_data and result_data['ReturnCode'] != 0:

			error_message = data[result_key].get('Message', '')
    
			# Capturing request details
			request_info = {
				"URL": url,
				"Method": method,
				"Headers": headers,
				"Body": body,
				"Params": params,
				"Files": files,
				"Response": data
			}

			detailed_message = f"Error in API response: {error_message}\n\nRequest Info: {request_info}"

			frappe.log_error(message=detailed_message, title=f"Request Error {result_key}")
			return data, False

		return data, True


	def get_customer(self, customer_code: str, log_error=True) -> Optional[JsonDict]:
		"""Get MymbAPIClient customer data for specified customer code.

		ref: https://documentation.mymb_b2c.com/docs/itemtype-get.html
		"""
		item, status = self.request(
			endpoint="/GetCliente", method="GET", params={"CodiceInternoCliente": customer_code}, log_error=log_error
		)
		if status:
			return item

	def get_addresses(self, customer_code: str, log_error=True) -> Optional[JsonDict]:
		"""Get MymbAPIClient adresses data for specified customer code.

		ref: https://documentation.mymb_b2c.com/docs/itemtype-get.html
		"""
		item, status = self.request(
			endpoint="/GetIndirizziCliente", method="GET", params={"CodiceInternoCliente": customer_code}, log_error=log_error
		)
		if status:
			return item
		
	def payment_deadline(self, customer_code: str, log_error=True) -> Optional[JsonDict]:
		"""Get MymbAPIClient deadlines data for specified customer code.

		ref: https://documentation.mymb_b2c.com/docs/itemtype-get.html
		"""
		item, status = self.request(
			endpoint="/GetListaScadenzeConInfo", method="GET", params={"CodiceInternoCliente": customer_code}, log_error=log_error
		)
		if status:
			return item
	
	def exposition(self, customer_code: str, log_error=True) -> Optional[JsonDict]:
		"""Get MymbAPIClient exposition data for specified customer code.

		ref: https://documentation.mymb_b2c.com/docs/itemtype-get.html
		"""
		item, status = self.request(
			endpoint="/GetEsposizioneClienteInfo", method="GET", params={"CodiceInternoCliente": customer_code}, log_error=log_error
		)
		if status:
			return item

	def get_multiple_prices(
        self,
        customer_code: str,
        address_code: str,
        item_codes: List[str],
        quantity_list: List[int],
        id_cart: str = '0',
        pricing_date: Optional[str] = None,
        load_packing_list: bool = True,
        calculate_availability: bool = True,
        calculate_arrivals: bool = False,
        calculate_previous_orders: bool = True,
        log_error=True,
	) -> Optional[JsonDict]:
        # If the pricing_date parameter is not passed, we assign it the current date
		if not pricing_date:
			from datetime import datetime
			pricing_date = datetime.now().strftime("%d%m%Y")

		# Initializing the parameters that are required to make the API call
		params = {
			'CodiceInternoCliente': customer_code,
			'CodiceIndirizzo': address_code,
			'ListaCodiciInterniArticolo': item_codes,
			'DataPrezzatura': pricing_date,
			'isCaricaListaImballi': load_packing_list,
			'isCalcolaDisponibilita': calculate_availability,
			'isCalcolaArrivi': calculate_arrivals,
			'isCalcolaOrdinatoInPrecedenza': calculate_previous_orders,
			'IdElaborazione': id_cart,
			'ListaQuantita': quantity_list
		}

		

		#
		# Check if item_codes is not empty
		if item_codes:
			# Making a POST request to the /GetPrezzaturaMultipla endpoint with the above parameters
			prices, status = self.request(
				endpoint="/GetPrezzaturaMultipla",
				method="POST",
				body=params,
				log_error=log_error
			)
		else:
			# Handle the case when item_codes is empty (return an error message, throw an exception, etc.)
			return {
					"error": "GetPrezzaturaMultiplaResult no items given",
					"params": params
				}, False

		# If the status of the API call is True, then process the received prices
		if status:
			try:
				# If the ReturnCode in the response is not 0, that indicates an error. So, log it and raise an Exception.
				if prices['GetPrezzaturaMultiplaResult']["ReturnCode"] != 0:
					error_message = prices['GetPrezzaturaMultiplaResult']['Message']
					frappe.log_error(message=f"An error occurred while fetching prices: {error_message}; Parameters: {params}", title="GetPrezzaturaMultiplaResult Error")
					raise Exception(f"Error: {error_message}")
				# If there is no error, then get the list of prices from the response
				prices_list = prices['GetPrezzaturaMultiplaResult']['ListaPrezzatura']
				product_data_list = []

				# For each price in the list, create a dictionary with all the necessary details
				for price in prices_list:
					product_data = {}
					# Initialize discount arrays

					# Process packaging options
					packaging_list = price.get('ImballiArticolo', {}).get('ListaImballoXArticolo', [])
					packaging_options = []

					for packaging in packaging_list:
						packaging_option = {
							"packaging_uom_description": packaging.get('DescrizioneUM'),
							"packaging_code": packaging.get('CodiceImballo1'),
							"packaging_is_default": packaging.get('IsImballoDiDefaultXVendita'),
							"packaging_is_smallest": packaging.get('IsImballoPiuPiccolo'),
							"qty_x_packaging": packaging.get('QtaXImballo'),
							"packaging_uom": packaging.get('UM')
						}
						packaging_options.append(packaging_option)

					# Assign packaging options to product data
					product_data["packaging_options"] = packaging_options

					# Initialize default_packaging with a default value
					default_packaging = {}

					# Check if packaging_options is not empty
					if packaging_options:
						# Default to the first option as a fallback
						default_packaging = packaging_options[0]

						# Search for packaging_is_default=True
						for option in packaging_options:
							if option['packaging_is_default']:
								default_packaging = option
								break
						else:
							# If no default, search for packaging_is_smallest=True
							for option in packaging_options:
								if option['packaging_is_smallest']:
									default_packaging = option
									break

					# Now, spread the default packaging into product_data
					product_data['default_packaging'] = default_packaging
					qty_x_default_packaging = default_packaging.get('qty_x_packaging', 1)


					# Assign the product ID, VAT percentage, gross price, and calculate the gross price with VAT
					product_data['item_code'] = price['CodiceInternoArticolo']
					product_data['vat_percent'] = price['IVAPercentuale']
					product_data['gross_price'] = price['Prezzo']*qty_x_default_packaging
					product_data['availability'] = price['QtaDisponibile']
					product_data['gross_price_with_vat'] = round(product_data['gross_price']* (1 + (product_data['vat_percent'] / 100)),4)
					riga_promozione_migliorativa = price.get('RigaPromozioneMigliorativa', {})

					# Check if an improving promotional offer exists based on same quantity request for the product and assign the corresponding values
					if riga_promozione_migliorativa and riga_promozione_migliorativa.get('CodicePromozione') is not None:
						# Assign all the details related to the improving promotional offer
						product_data['net_price'] = price['RigaPromozioneMigliorativa']['PrezzoNettoListinoDiRiferimento']*qty_x_default_packaging
						product_data['net_price_with_vat'] = round(product_data['net_price'] * (1 + (product_data['vat_percent'] / 100)),4)
						product_data['promo_price'] = price['RigaPromozioneMigliorativa']['PrezzoNettoConPromo']*qty_x_default_packaging
						product_data['promo_price_with_vat'] = round(product_data['promo_price'] * (1 + (product_data['vat_percent'] / 100)),4)
						product_data['promo_code'] = price['RigaPromozioneMigliorativa']['CodicePromozione']
						product_data['promo_row'] = price['RigaPromozioneMigliorativa']['RigaPromozione']
						product_data['is_best_promo'] = True
						product_data['is_promo'] = True
						product_data['promo_title']= price['RigaPromozioneMigliorativa']['TitoloPromozione']
						start_date = datetime.strptime(price['RigaPromozioneMigliorativa']['DataInizioValitita'], "%m/%d/%Y %H:%M:%S %p")
						end_date = datetime.strptime(price['RigaPromozioneMigliorativa']['DataFineValidita'], "%m/%d/%Y %H:%M:%S %p")
						product_data['start_promo_date'] = start_date.strftime("%d/%m/%y")
						product_data['end_promo_date'] = end_date.strftime("%d/%m/%y")

						# Initialize discount extra arrays
						product_data['discount_extra'] = [None] * 3
						product_data['discount_extra'][0] = price['RigaPromozioneMigliorativa']['ScontoExtra1']
						product_data['discount_extra'][1] = price['RigaPromozioneMigliorativa']['ScontoExtra2']
						product_data['discount_extra'][2] = price['RigaPromozioneMigliorativa']['ScontoExtra3']
					# If no promotional offer exists for the product, assign the net prices (with and without VAT) and set the promo flags to False
					else:
						product_data['net_price'] = price['PrezzoNettoXVisualizzazione']*qty_x_default_packaging
						product_data['net_price_with_vat'] =  price['PrezzoNettoIvatoXVisualizzazione']*qty_x_default_packaging
						product_data['is_best_promo'] = False
						product_data['is_promo'] = False
						

					product_data['discount'] = [None] * 6
					product_data['discount'][0] = price['ScontoORicarica1']
					product_data['discount'][1]= price['ScontoORicarica2']
					product_data['discount'][2] = price['ScontoORicarica3']
					product_data['discount'][3] = price['ScontoORicarica4']
					product_data['discount'][4] = price['ScontoORicarica5']
					product_data['discount'][5] = price['ScontoORicarica6']
					product_data["pricelist_type"] = price['TipoListinoUtilizzato']
					product_data["pricelist_code"] = price['CodiceListinoUtilizzato'] 
					product_data_list.append(product_data)

				return product_data_list

			except Exception as e:
				frappe.log_error(message=f"An error occurred while processing prices: {str(e)}; Parameters: {params}; Response:{prices}", title="GetPrezzaturaMultiplaResult Processing Error")
				# Return a dictionary with error details
				return {
					"error": "GetPrezzaturaMultiplaResult Processing Error",
					"params": params
				}, False

	def get_orders(self, args: Dict[str, Any]) -> Optional[JsonDict]:
		"""Get order headers with delivery information."""
		
		# Extract parameters from args
		cod_cliente = args.get('customer_code')
		type = args.get('type', 'T')  # 'T' as default
		address_code = args.get('address_code')
		date_from = args.get('date_from')
		date_to = args.get('date_to')
		rif_cliente = args.get('rif_cliente', '0')  # '0' as default
		

		endpoint = f"/GetTestateConInfoConsegna?CodiceInternoCliente={cod_cliente}&TipoEstrazione={type}&CodiceIndirizzo={address_code}"

		# Adding the date parameters if they're present
		if date_from and date_to:
			endpoint += f"&DataRegistrazioneIniziale={date_from}&DataRegistrazioneFinale={date_to}"

		# Add the IdRiferimentoCliente parameter
		endpoint += f"&IdRiferimentoCliente={rif_cliente}"

		data, status = self.request(endpoint=endpoint, method="GET", log_error=True)

		if status:
			order_data = data.get("GetTestateConInfoConsegnaResult", {}).get("ListaTestateConInfoConsegna", None)
			return order_data

		return None

	def get_ddt(self, args: Dict[str, Any]) -> Optional[JsonDict]:
		"""Get the delivery note (DDT) details."""

		# Extract parameters from args
		cod_cliente = args.get('customer_code')
		type = args.get('type', '')  # empty string as default if not provided
		address_code = args.get('address_code', '')  # empty string as default
		date_from = args.get('date_from')
		date_to = args.get('date_to')

		# Construct the service URL
		endpoint = (f"/GetTestateDDTConInfo?CodiceInternoCliente={cod_cliente}"
					f"&TipoEstrazione={type}&CodiceIndirizzo={address_code}")

		# Adding the date parameters if they're present
		if date_from and date_to:
			endpoint += f"&DataRegistrazioneIniziale={date_from}&DataRegistrazioneFinale={date_to}"

		data, status = self.request(endpoint=endpoint, method="GET", log_error=True)

		if status:
			ddt_data = data.get("GetTestateDDTConInfoResult", {}).get("ListaTestateDDTFATTConInfo", [])

			# Process the data
			for item in ddt_data:
				item["destination"] = item.get("DescrizioneEstesaIndirizzo", "")
				item["date"] = item.get("DataRegistrazione", "")
				doc_def = item.get("CausaleDocDefinitivo", "")
				anno_def = item.get("AnnoDocDefinitivo", "")
				num_def = item.get("NumeroDocDefinitivo", "")
				item["document"] = f"{doc_def}/{anno_def}/{num_def}"
				item["doc_type"] = doc_def
				item["invoice_number"] = num_def
				total_doc = item.get("TotaliDocumento", [0, 0, 0])
				item["taxable"] = total_doc[0]
				item["total"] = total_doc[2]
				item["scope"] = doc_def
				item["year"] = anno_def
				item["number"] = num_def
				item["type"] = item.get("TipoDocumento", "")
				item["type_bar_code"] = "D"
				item["bar_code_request"] = f"{doc_def}/{anno_def}/{num_def}/D"

			return ddt_data

		return None

	def get_invoices(self, args: Dict[str, Any]) -> Optional[JsonDict]:
		"""Get the invoice details."""

		# Extract parameters from args
		cod_cliente = args.get('customer_code')
		type = args.get('type', '')  # empty string as default if not provided
		address_code = args.get('address_code', '')  # empty string as default
		date_from = args.get('date_from')
		date_to = args.get('date_to')

		# Construct the service URL
		endpoint = (f"/GetTestateFATTConInfo?CodiceInternoCliente={cod_cliente}"
					f"&TipoEstrazione={type}&CodiceIndirizzo={address_code}")

		# Adding the date parameters if they're present
		if date_from and date_to:
			endpoint += f"&DataRegistrazioneIniziale={date_from}&DataRegistrazioneFinale={date_to}"

		data, status = self.request(endpoint=endpoint, method="GET", log_error=True)

		if status:
			invoice_data = data.get("GetTestateFATTConInfoResult", {}).get("ListaTestateDDTFATTConInfo", [])

			# Process the data
			for item in invoice_data:
				item["destination"] = item.get("DescrizioneEstesaIndirizzo", "")
				item["date"] = item.get("DataRegistrazione", "")
				doc_def = item.get("CausaleDocDefinitivo", "")
				anno_def = item.get("AnnoDocDefinitivo", "")
				num_def = item.get("NumeroDocDefinitivo", "")
				item["document"] = f"{doc_def}/{anno_def}/{num_def}"
				item["doc_type"] = doc_def
				item["invoice_number"] = num_def
				total_doc = item.get("TotaliDocumento", [0, 0, 0])
				item["taxable"] = total_doc[0]
				item["total"] = total_doc[2]
				item["scope"] = doc_def
				item["year"] = anno_def
				item["number"] = num_def
				item["type"] = item.get("TipoDocumento", "")
				item["type_bar_code"] = "I"
				item["bar_code_request"] = f"{doc_def}/{anno_def}/{num_def}/D"

			return invoice_data

		return None


	def get_latest_order_by_item(self, args: Dict[str, Any] , log_error=True) -> Optional[JsonDict]:
		"""Fetches the most recent order of a specific article by a customer. 
		"""

		# Extract parameters from args
		cod_cliente = args.get('customer_code')
		if cod_cliente is None:
			cod_cliente = args.get('client_id')
			
		item_id = args.get('item_id')

		item, status = self.request(
			endpoint="/GetUltimoOrdinatoClienteXArticolo", method="GET", params={"CodiceInternoCliente": cod_cliente , "CodiceInternoArticolo":item_id}, log_error=log_error
		)
		if status:
			return item
	
	def get_latest_order_by_list(self, args: Dict[str, Any], log_error=True) -> Optional[JsonDict]:
		"""Fetches the most recent order from the specified client and address code."""
		
		# Extract parameters from args
		client_id = args.get('client_id')
		address_code = args.get('latest_order_adress_code')

		# Check mandatory fields
		if not client_id:
			raise ValueError("client_id is a mandatory field")

		# Set default values for start_date and end_date if not provided
		if not args.get('start_date'):
			start_date = (datetime.now() - timedelta(days=90)).strftime('%d%m%Y')
		else:
			start_date = args.get('start_date')

		if not args.get('end_date'):
			end_date = datetime.now().strftime('%d%m%Y')
		else:
			end_date = args.get('end_date')

		is_only_latest = args.get('is_only_latest' , False)


		sku = args.get('sku', '')
		text_search = args.get('text_search', '')
		page = args.get('page', 1)
		per_page = args.get('per_page', 12)

		item, status = self.request(
			endpoint="/GetUltimoOrdinatoPerPeriodo",
			method="GET",
			params={
				"codiceInternoCliente": client_id,
				"codiceIndirizzo": address_code,
				"dataInizio": start_date,
				"dataFine": end_date,
				"codiceArticolo": sku,
				"descrizioneArticolo": text_search,
				"pagina": page,
				"elementiXPagina": per_page,
				"isCercaUltimoOrdine":is_only_latest
			},
			log_error=log_error
		)

		if status:
			return item
		return None
	
	def get_check_updated_exposition(self, args: Dict[str, Any] , log_error=True) -> Optional[JsonDict]:
		"""Fetches the updated exposition. 
		"""

		# Extract parameters from args
		cod_cliente = args.get('customer_code')
		if cod_cliente is None:
			cod_cliente = args.get('client_id')
			

		exposition, status = self.request(
			endpoint="/GetEsposizioneAggiornataB2B", method="GET", params={"CodiceInternoCliente": cod_cliente}, log_error=log_error
		)
		if status:
			return exposition
		

	def get_check_updated_deadlines(self, args: Dict[str, Any] , log_error=True) -> Optional[JsonDict]:
		"""Fetches updated deadlines. 
		"""

		# Extract parameters from args
		cod_cliente = args.get('customer_code')
		if cod_cliente is None:
			cod_cliente = args.get('client_id')
			

		exposition, status = self.request(
			endpoint="/GetScadenzeAggiornateB2B", method="GET", params={"CodiceInternoCliente": cod_cliente}, log_error=log_error
		)
		if status:
			return exposition
		
	def get_check_cart_anomalies(self, args: Dict[str, Any] , log_error=True) -> Optional[JsonDict]:
		"""Fetches anomalies in the cart. 
		"""
		# Extract parameters from args
		id_cart = args.get('id_cart')
		keep_issue_flag = args.get('keep_issue_flag', True)

		# Prepare the service URL, if true it does not fix anomalies in the cart
		if keep_issue_flag:
			endpoint = "/RisolviAnomalieDocumento"
			params = {"idElaborazione": id_cart, "isEstraiSoloAnomalie": keep_issue_flag}
		else:
			endpoint = "/RisolviAnomalieDocumento"
			params = {"idElaborazione": id_cart}

		# Make the GET request to the service
		anomalies_result, status = self.request(
			endpoint=endpoint, method="GET", params=params, log_error=log_error
		)

		if status:
			return anomalies_result
		
	def get_info_promotion_in_cart(self, args: Dict[str, Any], log_error: bool = True) -> Optional[Dict]:
		"""Fetches anomalies in the cart based on cart ID and promo details."""
		# Extract parameters from args
		id_cart = args.get('id_cart')
		promo_code = args.get('promo_code')
		promo_row = args.get('promo_row')
		row_id = args.get('row_id')

		# Define the endpoint and parameters for the API request
		endpoint = "/GetInfoPromozioneCarrello"
		params = {
			"IdElaborazione": id_cart,
			"IdRiga": row_id,
			"CodicePromozione": promo_code,
			"IdRigaPromozione": promo_row
		}

		# Make the GET request to the service
		anomalies_result, status = self.request(
			endpoint=endpoint, method="GET", params=params, log_error=log_error
		)

		# Check if the request was successful
		if status:
			return anomalies_result
		else:
			return None

	
	def info_availability_for_item(self, args: Dict[str, Any], log_error: bool = True) -> Optional[Dict[str, Any]]:
		"""Fetches availability information for items."""
		# Prepare the infoDisponibilitaXArticoloList payload
		item_list = args.get('item_list', [])
		endpoint = "/GetInfoDisponibilitaATPXArticolo"
		params = {
			"infoDisponibilitaXArticoloList": item_list
		}

		try:
			# Attempt to make the request
			data, status = self.request(
				endpoint=endpoint,
				method="POST",
				body=params,
				log_error=log_error
			)

			if status:
				# Success case, return data
				return data
			else:
				# Log error if request did not succeed
				frappe.log_error(
					message=f"Failed to fetch availability info; Parameters: {params}",
					title="info_availability_for_item Error"
				)
				return {
					"error": "Failed to fetch availability info",
					"params": params
				}
		except Exception as e:
			# Catch any unexpected exceptions and log them
			frappe.log_error(
				message=f"An error occurred while processing availability info: {str(e)}; Parameters: {params}",
				title="info_availability_for_item Processing Error"
			)
			return {
				"error": "Processing Error",
				"message": str(e),
				"params": params
			}
		
	def update_cart_row_with_date(self, args: Dict[str, Any], log_error: bool = True) -> Optional[Dict[str, Any]]:
		"""
		Updates the cart rows with availability information and date details for each item.

		This method prepares a payload with a list of items, including their respective availability dates and quantities,
		and sends it to the specified endpoint to update the cart rows with the latest data.

		Args:
			args (Dict[str, Any]): A dictionary containing 'item_list' (list of items) and 'id_cart' (cart identifier).
			log_error (bool): Flag to indicate if errors should be logged in the system (default is True).

		Returns:
			Optional[Dict[str, Any]]: Response data from the API or an error message in case of failure.
		"""
		# Prepare the payload with item availability information and cart ID
		item_list = args.get('item_list', [])
		id_cart = args.get('id_cart', 0)
		endpoint = "/UpdateRigheDocumentoConDatiATP"
		params = {
			"infoDisponibilitaXArticoloList": item_list,
			"idElaborazione": id_cart
		}

		try:
			# Attempt to make the request
			data, status = self.request(
				endpoint=endpoint,
				method="POST",
				body=params,
				log_error=log_error
			)

			if status:
				# Success case, return data
				return data
			else:
				# Log error if the request did not succeed
				frappe.log_error(
					message=f"Failed to update cart row with date; Parameters: {params}",
					title="update_cart_row_with_date Error"
				)
				return {
					"error": "Failed to update cart row with date",
					"params": params
				}
		except Exception as e:
			# Catch any unexpected exceptions and log them
			frappe.log_error(
				message=f"An error occurred while updating cart row with date: {str(e)}; Parameters: {params}",
				title="update_cart_row_with_date Processing Error"
			)
			return {
				"error": "Processing Error",
				"message": str(e),
				"params": params
			}

	def get_alternative_items(
		self,
		item_code: str,
		pricing_date: Optional[str] = None,
		id_elaborazione: str = "0",
		log_error=True
	) -> Optional[JsonDict]:
		"""
		Get alternative items for a given item code.

		Example API:
		/GetListaArticoliAlternativi?CodiceInternoArticolo=101552&IdElaborazione=0&DataPrezzatura=14052025
		"""

		from datetime import datetime

		if not pricing_date:
			pricing_date = datetime.now().strftime("%d%m%Y")  # Format like 14052025

		params = {
			"CodiceInternoArticolo": item_code,
			"IdElaborazione": id_elaborazione,
			"DataPrezzatura": pricing_date
		}

		try:
			result, status = self.request(
				endpoint="/GetListaArticoliAlternativi",
				method="GET",
				params=params,
				log_error=log_error
			)

			if status:
				# Assume the result contains a list of alternatives
				return result.get("GetListaArticoliAlternativiResult")

			return None

		except Exception as e:
			if log_error:
				frappe.log_error(
					title="GetListaArticoliAlternativi Error",
					message=f"Error while retrieving alternatives for item {item_code} | {str(e)} | Params: {params}"
				)
			return None
