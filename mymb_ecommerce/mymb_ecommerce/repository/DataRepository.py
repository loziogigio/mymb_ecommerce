class DataRepository:

    def __init__(self, session):
        self.session = session

    def get_data_by_entity_code(self, entity_code, last_operation=None):
        query = self.session.query(DataRepository).filter(
            and_(
                DataRepository.entity_code == entity_code,
                (DataRepository.lastoperation > last_operation) if last_operation else True
            )
        ).order_by(DataRepository.sorting)
        return query.all()

    def count_data_by_entity_code(self, entity_code, last_operation=None):
        query = self.session.query(DataRepository).filter(
            and_(
                DataRepository.entity_code == entity_code,
                (DataRepository.lastoperation > last_operation) if last_operation else True
            )
        )
        return query.count()
