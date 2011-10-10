from django.middleware.gzip import GZipMiddleware

class ImprovedGZipMiddleware(GZipMiddleware):
    """Will GZip the content if it's not application/octet-stream"""
    def process_response(self, request, response):
        ctype = response.get('Content-Type', '').lower()
        if ctype == "application/octet-stream":
            return response
        return super(ImprovedGZipMiddleware, self).process_response(request, response)