from opensearchpy import OpenSearch

host = '192.168.2.2'
port = 9200
auth = ('admin', 'admin')  # For testing only. Don't store credentials in code.
opensearch = OpenSearch(
    hosts=[{'host': host, 'port': port}],
    http_compress=True,  # enables gzip compression for request bodies
    http_auth=auth,
    use_ssl=False,
    verify_certs=False,
    ssl_assert_hostname=False,
    ssl_show_warn=False,
)


def create_index():
    if not opensearch.indices.exists('posts'):
        opensearch.indices.create('posts', body={
            'settings': {
                'index': {
                    'number_of_shards': 1
                }
            }
        })
