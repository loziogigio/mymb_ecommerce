import base64
from typing import Any, Dict, List, Optional, Tuple

import frappe
import requests
from frappe import _
from frappe.utils import cint, cstr, get_datetime
from pytz import timezone

from mymb_ecommerce.mymb_b2c.constants import SETTINGS_DOCTYPE
from mymb_ecommerce.mymb_b2c.utils import create_mymb_b2c_log
from frappe.utils.password import get_decrypted_password
from datetime import datetime

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

	def __initialize_auth(self):
		"""Initialize and setup authentication details"""
		encoded_credentials = base64.b64encode(f'{self.api_username}:{self.api_password}'.encode('utf-8')).decode('utf-8')
		self._auth_headers = {"Authorization": f"Basic {encoded_credentials}"}

	
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
			response = requests.request(
				url=url, method=method, headers=headers, json=body, params=params, files=files
			)
			# mymb_b2c gives useful info in response text, show it in error logs
			response.reason = cstr(response.reason) + cstr(response.text)
			response.raise_for_status()
		except Exception as e:
			frappe.log_error(message=f"An error occurred while : {str(e)}", title="Request")
			if log_error:
				create_mymb_b2c_log(status="Error", make_new=True)
			return None, False

		if method == "GET" and "application/json" not in response.headers.get("content-type"):
			return response.content, True

		# Parse the response content
		data = response.json()

		# Get the key of the main result object. This assumes that your response 
		# always has a single key at the top level.
		result_key = list(data.keys())[0] if data and isinstance(data, dict) else None

		# Check if ReturnCode is not 0 in the response and log the error
		if result_key and data.get(result_key, {}).get('ReturnCode') != 0:
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

					# Assign the product ID, VAT percentage, gross price, and calculate the gross price with VAT
					product_data['item_code'] = price['CodiceInternoArticolo']
					product_data['vat_percent'] = price['IVAPercentuale']
					product_data['gross_price'] = price['Prezzo']
					product_data['availability'] = price['QtaDisponibile']
					product_data['gross_price_with_vat'] = round(product_data['gross_price']* (1 + (product_data['vat_percent'] / 100)),4)
					riga_promozione_migliorativa = price.get('RigaPromozioneMigliorativa', {})

					# Check if an improving promotional offer exists based on same quantity request for the product and assign the corresponding values
					if riga_promozione_migliorativa and riga_promozione_migliorativa.get('CodicePromozione') is not None:
						# Assign all the details related to the improving promotional offer
						product_data['net_price'] = price['RigaPromozioneMigliorativa']['PrezzoNettoListinoDiRiferimento']
						product_data['net_price_with_vat'] = round(product_data['net_price'] * (1 + (product_data['vat_percent'] / 100)),4)
						product_data['promo_price'] = price['RigaPromozioneMigliorativa']['PrezzoNettoConPromo']
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
						product_data['net_price'] = price['PrezzoNettoXVisualizzazione']
						product_data['net_price_with_vat'] =  price['PrezzoNettoIvatoXVisualizzazione']
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
		
		# Handling the type 'T' case to determine date_from and date_to
		if type == 'T':
			current_date = datetime.now().strftime('%d%m%Y')
			date_from = current_date
			date_to = current_date

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
		endpoint = (f"/GetTestateFATTConInfo?CodiceInternoCliente={cod_cliente}"
					f"&TipoEstrazione={type}&CodiceIndirizzo={address_code}")

		# Adding the date parameters if they're present
		if date_from and date_to:
			endpoint += f"&DataRegistrazioneIniziale={date_from}&DataRegistrazioneFinale={date_to}"

		data, status = self.request(endpoint=endpoint, method="GET", log_error=True)

		if status:
			ddt_data = data.get("GetTestateFATTConInfoResult", {}).get("ListaTestateDDTFATTConInfo", [])

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
				item["type_bar_code"] = "I"
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
