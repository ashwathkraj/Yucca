from google.cloud import vision
from google.cloud import storage
from google.cloud import datastore

def verify_blobs(bucket_name):
	"""
		Verify if bucket images fit certain labels
	"""
	#Variable Initialization
	client = vision.ImageAnnotatorClient()
	image = vision.types.Image()
	datastore_client = datastore.Client()
	storage_client = storage.Client()
	bucket = storage_client.get_bucket(bucket_name)
	new_blobs = {}
	kind = "trash-site"

	#Collect all unverified images from Datastore
	query = datastore_client.query(kind=kind)
	# query.add_filter("valid", "=", False)
	results = list(query.fetch())

	#Get blobs, which are the images we are measuring
	blobs = bucket.list_blobs()

	#If an unverified image matches a photo-id, then add it to a dictionary mapping id to image name
	#If you want to avoid rechecking photos that you've already marked False, then use a string instead of a boolean and filter out for "checked"
	#This depends on whether the photo-ids match blob names when inputted through twilio
	for blob in blobs:
		for result in results:
			if (result["photo-id"]==blob.name): 
				new_blobs[result.id] = blob.name
	
	#Use Vision API to check labels and determine the identity of the image
	for inp,outp in new_blobs.items():
		image.source.image_uri = ("gs://ramranch-images//" + outp)
		response = client.label_detection(image=image)
		labels = response.label_annotations
		print("Labels: ")
		for label in labels:
			print("\t",label.description)
			if ("waste" or "trash" or "litter") in label.description:
				#Send positive status to database
				print(outp, " is a valid image")
				with datastore_client.transaction():
					key = datastore_client.key(kind, inp)
					data = datastore_client.get(key)
					data["valid"] = True
					datastore_client.put(data)
				break

def hello_gcs(event, context):
    """Triggered by a change to a Cloud Storage bucket.
    Args:
         event (dict): Event payload.
         context (google.cloud.functions.Context): Metadata for the event.
    """
    file = event
    print(f"Processing file: {file['name']}.")
    verify_blobs("ramranch-images")
    
