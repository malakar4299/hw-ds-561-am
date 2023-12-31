from flask import Flask, Response, abort, request,escape
from google.cloud import storage
from google.cloud import logging as gcloud_logging
import requests
import functions_framework
from flask_cors import cross_origin
from google.cloud import pubsub_v1
import json

app = Flask(__name__)

# Initialize an anonymous client
storage_client = storage.Client.create_anonymous_client()

bucket = storage_client.bucket('hw-2-files-bucket')

# Set up Google Cloud Logging
logging_client = gcloud_logging.Client()
logger = logging_client.logger('gcs-file-requests')

BANNED_COUNTRIES = ['North Korea', 'Iran', 'Cuba', 'Myanmar', 'Iraq', 'Libya', 'Sudan', 'Zimbabwe', 'Syria']
SECOND_APP_URL = "http://localhost:5001/alert"


@cross_origin()
@functions_framework.http
def serve_file(request):
    path = (request.path)
    filename = path.strip("/")
    # Check HTTP method
    country = request.headers.get('X-country')
    if country in BANNED_COUNTRIES:
        # Initialize publisher client
        logger.log_text(f"APP 1 logging: banned country : {country} for file: {filename}")
        publisher = pubsub_v1.PublisherClient()
        topic_path = publisher.topic_path('ds-561-am', 'banned-message-handler')
        data = {
            'country': country,
            'ip': request.headers.get('X-client-IP'),
            'filename': filename
        }

        """Publish details of a request from a banned country to Pub/Sub."""
        publisher.publish(topic_path, data=json.dumps(data).encode("utf-8"))
        # requests.post(SECOND_APP_URL, json=data)
        return "Permission Denied", 400


    if request.method != 'GET':
        logger.log_text(f"Erroneous request method {request.method} for file: {filename}")
        return "Not Implemented", 501

    blob = bucket.blob('files/' + filename)
    if not blob.exists():
        logger.log_text(f"File not found, this is being logged from the code: {filename}")
        abort(404)

    content = blob.download_as_text()
    return Response(content, mimetype='text/html'), 200  # Adjust the mimetype based on your file types


if __name__ == '__main__':
    app.run(debug=True)
