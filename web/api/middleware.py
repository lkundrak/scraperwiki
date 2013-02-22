# Taken wholesale from https://github.com/scdoshi/django-cors/blob/master/cors.py

from django.conf import settings

#: By default we'll set CORS Allow Origin * for all application/json responses within /api/
DEFAULT_CORS_PATHS = (
	('/api/', ('application/json', ),('*',), ),
)

class CORSMiddleware(object):
	"""
	From https://github.com/acdha/django-sugar/blob/master/sugar/middleware/cors.py

	Middleware that serves up representations with a CORS header to
	allow third parties to use your web api from JavaScript without
	requiring them to proxy it.

	See: http://www.w3.org/TR/cors/
	"""

	def __init__(self):
		self.paths = DEFAULT_CORS_PATHS

	def process_response(self, request, response):
		content_type = response.get('content-type', '').split(";")[0].lower()

		for path, types, allowed in self.paths:
			if request.path.startswith(path):
				for domain in allowed:
					response['Access-Control-Allow-Origin'] = domain
					response['Access-Control-Allow-Methods'] = 'POST, GET'
					response['Access-Control-Max-Age'] = 1000
					response['Access-Control-Allow-Headers'] = '*'
				break
		return response