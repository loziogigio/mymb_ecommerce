from sqlalchemy import and_, or_, text
from sqlalchemy.orm import sessionmaker
from mymb_ecommerce.model.Feature import Feature
from mymb_ecommerce.model.ProductFeature import ProductFeature
from mymb_ecommerce.model.SubmenuProduct import SubmenuProduct
from mymb_ecommerce.model.FamilyProductFeature import FamilyProductFeature
from mymb_ecommerce.model.ChannelFamilyProductFeature import ChannelFamilyProductFeature
from mymb_ecommerce.mymb_b2c.settings.configurations import Configurations

class FeatureRepository:

    def __init__(self):
        # Get the Configurations instance
        config = Configurations()

        # Get the database connection from Configurations class
        db = config.get_mysql_connection(is_data_property=True)
        engine = db.engine
        Session = sessionmaker(bind=engine)
        self.session = Session()

    def __del__(self):
        self.session.close()

    def get_features_by_entity_codes(self, entity_codes , channel_id=None , return_result = False):
        # Create the query with the necessary joins and filtering
        query = self.session.query(
            ProductFeature.product_code,
            ProductFeature.feature_id,
            Feature.label,
            ProductFeature.datedata,
            ProductFeature.stringdata,
            ProductFeature.numericdata,
            ProductFeature.booleandata,
            ProductFeature.uom_id,
            ChannelFamilyProductFeature.usedforsearch.label('used_search'),
            ChannelFamilyProductFeature.usedforfacet.label('used_search_default'),
            ChannelFamilyProductFeature.featureidusedinsearch.label('ft_id_search'),
            ChannelFamilyProductFeature.featureidusedinsearch.label('ft_id_search_default')
        ).join(
            SubmenuProduct, SubmenuProduct.product_code == ProductFeature.product_code
        ).join(
            Feature, Feature.feature_id == ProductFeature.feature_id
        ).outerjoin(
            ChannelFamilyProductFeature, 
            and_(
                ChannelFamilyProductFeature.family_id == SubmenuProduct.submenu_id,
                ChannelFamilyProductFeature.feature_id == ProductFeature.feature_id,
                # Conditionally apply the channel filter
                *[
                    ChannelFamilyProductFeature.channel_id.in_(channel_id.split(',')) if channel_id
                    else text('1=1')  # If no channel_id, skip this filter
                ]
            )
        ).filter(
            ProductFeature.product_code.in_(entity_codes)
        ).order_by(ProductFeature.product_code, ProductFeature.feature_id)

        # Fetch the results
        results = query.all()

        if return_result:       
        # Prepare the associative result: dictionary where product_code maps to its features
            features_by_product = {}

            for row in results:
                # Convert row to dictionary using _asdict
                row_dict = row._asdict()

                product_code = row_dict['product_code']
                label = row_dict['label']
                uom_id = row_dict['uom_id']

                # Determine the value (string, numeric, or boolean)
                value = row_dict['stringdata'] or row_dict['numericdata'] or ('true' if row_dict['booleandata'] else 'false')

                # Add the feature to the dictionary
                features_by_product[label] = {
                    "value": value,
                    "default_uom": uom_id
                }

            return features_by_product

        # Initialize a dictionary to group features by product_code
        product_features = {}

        # Process the results into a dictionary, grouped by product_code
        for feature in results:
            product_code = feature.product_code
            if product_code not in product_features:
                product_features[product_code] = {}
            
            fieldname = f"field_{feature.feature_id}"
            fieldvalue = ''

            if feature.datedata:
                fieldname += '_feature_dt'
                fieldvalue = feature.datedata

            if feature.stringdata:
                fieldname += '_feature_s'
                fieldvalue = feature.stringdata

            if feature.numericdata:
                fieldname += '_feature_f'
                fieldvalue = feature.numericdata

            if feature.booleandata is not None:
                fieldname += '_feature_b'
                fieldvalue = 'true' if feature.booleandata else 'false'

            # Add the field value to the product's feature dictionary
            product_features[product_code][fieldname] = fieldvalue

        return product_features
    

    def get_features_by_family_id_b2c(self, family_id):
        # Create the query with the necessary joins and filtering
        query = self.session.query(
            Feature.feature_id,
            Feature.datatype,
            Feature.uom_id,
            FamilyProductFeature.family_id,
            FamilyProductFeature.label
        ).join(
            FamilyProductFeature, Feature.feature_id == FamilyProductFeature.feature_id
        ).filter(
            FamilyProductFeature.family_id == family_id
        )

        results = query.all()

        # Prepare the dictionary to store facet fields
        facet_fields = {}

        # Process the results
        for result in results:
            feature_id = result.feature_id
            datatype = result.datatype
            uom_id = result.uom_id
            label = result.label

            # Determine the facet field name based on the datatype
            if datatype == 'A':
                facet_name_field = f"field_{feature_id}_feature_s"
                feature_type='string'
            elif datatype == 'N':
                facet_name_field = f"field_{feature_id}_feature_f"
                feature_type='float'
            elif datatype == 'D':
                facet_name_field = f"field_{feature_id}_feature_d"
                feature_type='datetime'
            elif datatype == 'B':
                facet_name_field = f"field_{feature_id}_feature_b"
                feature_type='boolean'
            else:
                # Skip if the datatype doesn't match any of the expected values
                continue

            # Add the facet name field to the dictionary
            facet_fields[facet_name_field] = {
                "feature_id": feature_id,
                "datatype": datatype,
                "feature_type": feature_type,
                "uom_id":uom_id,
                "label":label
            }

        return facet_fields
