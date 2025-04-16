import json

from requests import HTTPError

class EventPortalException(Exception):
    def __init__(self, code, name, detail=None):
        self.code=code
        self.name=name
        self.detail = detail

class BrokerException(Exception):
    def __init__(self, code, name, detail=None):
        self.code=code
        self.name=name
        self.detail = detail

class UnprocessableEntity(HTTPError):
    def __init__(self, request, response):
        rq_json = next(iter(json.loads(request.body.decode()).values()))
        errors = response.json()

        for field, error in errors.items():
            rq_field = rq_json.get(field, None)
            if not rq_field:
                continue

            if isinstance(error, list):
                error = error.insert(0, rq_field)
            elif isinstance(error, str):
                error = f"{rq_field} {error}"

        msg = json.dumps(errors)
        super(HTTPError, self).__init__(msg, request=request, response=response)