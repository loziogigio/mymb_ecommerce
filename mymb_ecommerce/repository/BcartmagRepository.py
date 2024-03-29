# mymb_ecommerce/mymb_ecommerce/repository/BcartmagRepository.py

from mymb_ecommerce.model.Bcartmag import Bcartmag , get_bcartmag_full_tablename
from mymb_ecommerce.model.MyPrecod import MyPrecod , get_myprecod_full_tablename
from mymb_ecommerce.model.MyBarcod import MyBarcod , get_mybarcod_full_tablename
from mymb_ecommerce.model.ChannelProduct import ChannellProduct , get_channel_product_full_tablename
from mymb_ecommerce.mymb_b2c.settings.configurations import Configurations
from datetime import datetime, timedelta
from sqlalchemy.orm import sessionmaker, joinedload
from sqlalchemy import text , create_engine, desc, and_  ,select


class BcartmagRepository:

    def __init__(self, external_db_connection_string=None):
        # Get the Configurations instance
        config = Configurations()

        # If an external DB connection string is provided, use it. Otherwise, use the default connection
        if external_db_connection_string:
            engine = create_engine(external_db_connection_string)
        else:
            db = config.get_mysql_connection(is_erp_db=True)
            engine = db.engine

        Session = sessionmaker(bind=engine)
        self.session = Session()

    def __del__(self):
        self.session.close()

    def get_all_records(self, limit=None, page=None, time_laps=None, to_dict=False, filters=None  , channel_id=None):
        if channel_id:
            filters["channel_id"] = channel_id
            return self.get_all_records_by_channell_product( limit=limit, page=page, time_laps=time_laps, to_dict=to_dict, filters=filters)
        
        # query = self.session.query(Bcartmag)

        # Query with an inner join on MyPrecod
        query = self.session.query(Bcartmag , MyPrecod.tprec_darti).join(
            MyPrecod, and_(
                MyPrecod.cprec_darti == Bcartmag.cprec_darti,
                MyPrecod.csoci == Bcartmag.csoci
            )
        )

        if time_laps is not None:
            time_laps = int(time_laps)
            time_threshold = datetime.now() - timedelta(minutes=time_laps)
            query = query.filter(Bcartmag.created_at >= time_threshold)

        # Apply the filters
        if filters is not None:
            for key, value in filters.items():
                # Make sure the attribute exists in the Bcartmag model
                if hasattr(Bcartmag, key):
                    if isinstance(value, list):
                        # If the value is a list, use the IN statement
                        query = query.filter(getattr(Bcartmag, key).in_(value))
                    else:
                        # Else, use the equality filter
                        query = query.filter(getattr(Bcartmag, key) == value)

        # Order by dinse_ianag in descending order
        query = query.order_by(desc(Bcartmag.dinse_ianag))
        
        # Apply limit and offset for pagination
        if limit is not None:
            query = query.limit(limit)
            if page is not None and page > 1:
                query = query.offset((page - 1) * limit)

        results = query.all()

        # Process results
        if to_dict:
            return [{**bcartmag.to_dict(), "tprec_darti": tprec_darti} for bcartmag, tprec_darti in results]
        else:
            processed_results = []
            for bcartmag, tprec_darti in results:
                bcartmag_dict = bcartmag.to_dict() if hasattr(bcartmag, 'to_dict') else bcartmag
                bcartmag_dict['tprec_darti'] = tprec_darti
                processed_results.append(bcartmag_dict)
            return processed_results
        
    def get_all_records_by_channell_product(self, limit=None, page=None, time_laps=None, to_dict=False, filters=None):
        
        bcartmag = get_bcartmag_full_tablename()
        channel_product = get_channel_product_full_tablename()
        myprecod = get_myprecod_full_tablename() 
        mybarcod = get_mybarcod_full_tablename() 

        mybarcod_subquery = f"""
        (SELECT mb.cbarx FROM {mybarcod} AS mb
         WHERE mb.csoci = b.csoci AND mb.oarti = b.oarti
         ORDER BY mb.daggi DESC, mb.bbarx_sazie ASC LIMIT 1)
        """
        
        # Base SQL query
        sql_query_str = f"""
            SELECT b.*, c.channel_id, c.lastoperation , {mybarcod_subquery} AS barcode , m.tprec_darti as brand
            FROM {bcartmag} AS b
            INNER JOIN {channel_product} AS c ON b.oarti = c.product_code
            INNER JOIN {myprecod} AS m ON m.cprec_darti = b.cprec_darti AND m.csoci = b.csoci
        """
        
        # List to hold our filter conditions and their parameters
        conditions = []
        params = {}
        
        # Filter by time_laps if provided
        if time_laps is not None:
            time_laps = int(time_laps)
            time_threshold = datetime.now() - timedelta(minutes=time_laps)
            conditions.append("b.created_at >= :time_threshold")
            params["time_threshold"] = time_threshold

        # Apply other filters
        if filters:
            for key, value in filters.items():
                if hasattr(Bcartmag, key):
                    table_prefix = "b"
                elif hasattr(ChannellProduct, key):
                    table_prefix = "c"
                else:
                    continue  # Skip if attribute does not exist in either model

                if isinstance(value, list):
                    # Handling list values using the IN statement
                    placeholder = f"{key}_list"
                    conditions.append(f"{table_prefix}.{key} IN :{placeholder}")
                    params[placeholder] = value
                else:
                    # Handling single values using equality
                    conditions.append(f"{table_prefix}.{key} = :{key}")
                    params[key] = value


        # If we have any conditions, add them to the SQL
        if conditions:
            sql_query_str += " WHERE " + " AND ".join(conditions)
        
        # Order by dinse_ianag in descending order
        sql_query_str += " ORDER BY b.dinse_ianag DESC"

        # Apply limit and offset for pagination
        if limit is not None:
            sql_query_str += " LIMIT :limit"
            params["limit"] = limit
            if page is not None and page > 1:
                offset = (page - 1) * limit
                sql_query_str += " OFFSET :offset"
                params["offset"] = offset

        # Convert the SQL string to a TextClause
        sql_query = text(sql_query_str)

        # Execute the SQL query
        result = self.session.execute(sql_query, params)

        # Fetch all rows from the result
        rows = result.all()

        if to_dict:
            # Use the _mapping attribute to extract the columns as key-value pairs for each row.
            results = [dict(row._mapping) for row in rows]
        else:
            results = rows

        return results
            
    
    def get_record_count_by_channell_product(self, time_laps=None, filters=None , channel_id=None):
        
        if channel_id:
            filters['channel_id'] = channel_id
            
        bcartmag = get_bcartmag_full_tablename()
        channel_product = get_channel_product_full_tablename()
        
        # Base SQL query
        sql_query_str = f"""
            SELECT COUNT(*)
            FROM {bcartmag} AS b
            INNER JOIN {channel_product} AS c ON b.oarti = c.product_code
        """
        
        # List to hold our filter conditions and their parameters
        conditions = []
        params = {}
        
        # Filter by time_laps if provided
        if time_laps is not None:
            time_laps = int(time_laps)
            time_threshold = datetime.now() - timedelta(minutes=time_laps)
            conditions.append("b.created_at >= :time_threshold")
            params["time_threshold"] = time_threshold

        # Apply other filters
        if filters:
            for key, value in filters.items():
                if hasattr(Bcartmag, key):
                    table_prefix = "b"
                    conditions.append(f"{table_prefix}.{key} = :{key}")
                    params[key] = value
                elif hasattr(ChannellProduct, key):
                    table_prefix = "c"
                    conditions.append(f"{table_prefix}.{key} = :{key}")
                    params[key] = value

        # If we have any conditions, add them to the SQL
        if conditions:
            sql_query_str += " WHERE " + " AND ".join(conditions)
        
        # Convert the SQL string to a TextClause
        sql_query = text(sql_query_str)

        # Execute the SQL query
        result = self.session.execute(sql_query, params)

        # Fetch the count from the result
        count = result.scalar()

        return count



