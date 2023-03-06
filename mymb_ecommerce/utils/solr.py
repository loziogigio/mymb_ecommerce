import pysolr

class Solr:
    def __init__(self, url, **kwargs):
        self.solr = pysolr.Solr(url, **kwargs)

    def search(self, q, start=0, rows=10, sort=None, facet_fields=None, **kwargs):
        """
        Execute a Solr search query and return the results.

        :param q: str - The query string.
        :param start: int - The starting index of the search results (default: 0).
        :param rows: int - The number of search results to return (default: 10).
        :param sort: str - The sorting criteria for the search results (default: None).
        :param facet_fields: list - The fields to facet on (default: None).
        :param **kwargs: Additional Solr query parameters as keyword arguments.
        :return: dict - A dictionary containing the search results and facet counts.
        """
        params = {
            'q': q,
            'start': start,
            'rows': rows
        }

        if sort:
            params['sort'] = sort

        if facet_fields:
            params['facet'] = 'on'
            params['facet.field'] = facet_fields

        params.update(kwargs)

        response = self.solr.search(**params)

        # Get the search results
        results = [dict(result) for result in response]

        # Get the facet counts
        facet_counts = {}
        if 'facet_counts' in response.raw_response:
            for field, counts in response.raw_response['facet_counts']['facet_fields'].items():
                facet_counts[field] = dict(zip(counts[::2], counts[1::2]))

        # Return the results and facet counts as a dictionary
        return {
            'results': results,
            'facet_counts': facet_counts,
            'hits':response.hits
        }
