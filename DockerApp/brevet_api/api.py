# Brevet RESTful API
# Author: Andrew Werderman

import arrow
import flask
from flask import (
	Flask, redirect, url_for, request, render_template, Response, jsonify 
	)
from flask_restful import Resource, Api
from pymongo import MongoClient
from itsdangerous import (TimedJSONWebSignatureSerializer
							as Serializer, BadSignature,
							SignatureExpired)
from passlib.apps import custom_app_context as pwd_context
from basicauth import decode


# Instantiate the app
app = Flask(__name__)
api = Api(app=app, catch_all_404s=True)
app.config['SECRET_KEY'] = 'the quick brown fox jumps over the lazy dog'

# Create Mongo instance
client = MongoClient('mongodb://mongo:27017/')
brevetdb = client['brevetdb'] 
usersdb = client['usersdb']

class Home(Resource):
	def get(self):
		return ''


class Register(Resource):
	def __init__(self):
		self.collection = usersdb['UserInfo']

	def post(self):
		'''
		Function executed on a POST request to register. If the username is not
		taken, the function will:
		  1. Hash the user's desired password
		  2. Insert the username and hashed password in the usersdb database.
		  3. Return a JSON object of the unique user_id, username, and date_added
		  with a status code of 201.

		Upon failure, an error with status code 400 (bad request) is returned.

		USE: curl -d "username=jeffrey&password=admin" localhost:5001/api/register
		'''
		#Get arguements from cURL
		username = request.form.get('username')
		password = request.form.get('password')

		# Handle username is already in use. (True: return appropriate message)
		if (self.collection.find_one({'username': username})):
			# Bad Request is returned
			return {'Error': '{} already in use.'.format(username)}, 400

		# Handle invalid inputs
		if ((username == None) or (username == '')) or ((password == None) or (password == '')):
			return {'Error': 'Please provide a username and password.'}, 400

		# Hash password
		hVal = pwd_context.encrypt(password)

		# Insert: {'username': username, 'password': hVal} into self.collection
		self.collection.insert_one({'username': username, 'password': hVal})

		# Get user object
		user = self.collection.find_one({'username': username})

		# Format response
		info = {'location': str(user['_id']), 'username': username, 'date_added': arrow.now().for_json()}
		response = flask.jsonify(info)
		response.status_code = 201
		return response


class Token(Resource):
	def __init__(self):
		self.collection = usersdb['UserInfo']

	def get(self):
		'''
		Function executed on a 'GET /api/token' request. Upon request,
		this function will:
		  1. Authenticate the user with a verify_password() call.
		  2. Set an expiration (in seconds) on the token.
		  3. Return a JSON object of the requested token, and 
		  duration of the token.
		
		On failure, an error message with status code 401 (unauthorized) is returned.

		USE: curl -u "jeffrey:admin" localhost:5001/api/token
		'''
		message = request.headers.get('Authorization')
		username, password = decode(message)

		if not (self.collection.find_one({'username': username})):
			return {'Error': 'User does not exist.'}, 401

		if not (Token.verify_password(self, username, password)):
			return {'Error': 'Unauthorized'}, 401

		duration = 600
		token = Token.generate_auth_token(self, username, duration)
		info = {'token': str(token), 'duration': duration}

		response = flask.jsonify(info)
		response.status_code = 200
		return response 

	def verify_password(self, username, password):
		'''
		inputs: username and password
		output: True for correct password, else False

		Check inputted password against saved hashed password, and 
		return True or False depending on whether the password is correct or not.
		'''
		user = self.collection.find_one({'username': username})
		hashVal = user['password']
		return pwd_context.verify(password, hashVal)

	def generate_auth_token(self, username, expiration=600):
		'''
		inputs: username and expiration (the approx. number of seconds before 
				the expiration of the token)
		output: authentication token
		'''
		s = Serializer(app.config['SECRET_KEY'], expires_in=expiration)
		user = self.collection.find_one({'username': username})
		return s.dumps({'id': str(user['_id'])})


# Can only be accessed with the correct token.
class ListBrevet(Resource):
	def __init__(self):
		#******** Change to be user specific *************
		self.collection = brevetdb['brevet'] 

	def get(self, items='listAll', resultFormat='json'):
		'''
		  Input:
			items - which items to list: 'listAll' (default), 'listOpenOnly', 'listCloseOnly'
			resultFormat - requested format of response
		  Output:
			array of brevet control open and/or close times
			resultFormat='json' gives an array of dictionaries
			resultFormat='csv' gives an array of arrays

		curl -u "<tokenstring>:none" localhost:5001/api/token
		'''
		top = request.args.get('top')

		# Handle empty brevet
		if self.collection.count() == 0:
			return jsonify({'Error': 'Empty Brevet'})

		# Handle unexpected query.
		if (items not in ['listAll', 'listOpenOnly', 'listCloseOnly']) or (resultFormat not in ['json', 'csv']):
			return jsonify({'Error': 'Invalid Query'})

		# Handle whether top is set or not
		if (top == None) or (top == ''):
			controls = self.collection.find()
		else:
			# Handle invalid input for top
			try:
				limit = int(top)
				if(limit <= 0):
					return jsonify({'Error': 'Invalid number of top elements'})
				else:
					controls = self.collection.find(limit=limit) # limits the number of results in find()
			except ValueError:
				return jsonify({'Error': 'Value Error for top'})

		# Populate results with queried output
		if (items == 'listAll'):
			result = ListBrevet.formatResponse(controls, resultFormat, 'open_time', 'close_time')
		elif (items == 'listOpenOnly'):
			result = ListBrevet.formatResponse(controls, resultFormat, 'open_time')
		else: # resultFormat == 'listCloseOnly'
			result = ListBrevet.formatResponse(controls, resultFormat, 'close_time')
		
		if (resultFormat == 'csv'):
			return Response(result, mimetype='text/csv')

		return jsonify(result)

	def formatResponse(brevet, resultFormat, *args):
		'''
		  Input: 
		  	brevet - the db brevet collection instance
		  	resultFormat - the desired output format of the query -- 'json' or 'csv'
		  	*args - the key values of the desired control information -- 'open_time'/'close_time'/etc.
		  Output: 
		  	json - an array of dictionaries of control info
		  	csv - A string formatted to csv
		  Helper function to format the queried resultFormat of controls.
		'''
		json = []
		csv = ''
		if (resultFormat == 'json'):
			for ctrl in brevet:
				jsonDict = {key:ctrl[key] for key in args}
				json.append(jsonDict)
		else:
			csv += str(args[0])
			if (len(args) > 1):
				csv += ', {}\n'.format(args[1])
				for ctrl in brevet:
					csv += '{}, {}\n'.format(ctrl[args[0]], ctrl[args[1]])
			else:
				csv += '\n'
				for ctrl in brevet:
					csv += '{}\n'.format(ctrl[args[0]])

		output = {'json': json, 'csv': csv}
		return output[resultFormat]

	def verify_auth_token(token):
		s = Serializer(app.config['SECRET_KEY'])
		try:
			data = s.loads(token)
		except SignatureExpired:
			return None    # valid token, but expired
		except BadSignature:
			return None    # invalid token
		return "Success"


# Create routes
api.add_resource(Home, '/')
api.add_resource(Token, '/api/token')
api.add_resource(Register, '/api/register')
api.add_resource(ListBrevet, '/api/<items>/<resultFormat>')

# Run the application
if __name__ == '__main__':
    app.run(
    	host='0.0.0.0', 
    	port=80, 
    	debug=True,
    	extra_files = './templates/response.html')

