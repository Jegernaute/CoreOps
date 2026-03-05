from rest_framework.pagination import PageNumberPagination

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size' # Дозволяє клієнту просити певну кількість записів (?page_size=50)
    max_page_size = 100 # Максимум, який дозволить віддати за один запит