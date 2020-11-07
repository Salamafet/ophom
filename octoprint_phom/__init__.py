# coding=utf-8
from __future__ import absolute_import

### (Don't forget to remove me)
# This is a basic skeleton for your plugin's __init__.py. You probably want to adjust the class name of your plugin
# as well as the plugin mixins it's subclassing from. This is really just a basic skeleton to get you started,
# defining your plugin as a template plugin, settings and asset plugin. Feel free to add or remove mixins
# as necessary.
#
# Take a look at the documentation on what other plugin mixins are available.

import octoprint.plugin
from octoprint.util import RepeatedTimer
import flask
import requests
import re
import time

class OphomPlugin(octoprint.plugin.SettingsPlugin,
                  octoprint.plugin.AssetPlugin,
                  octoprint.plugin.TemplatePlugin,
				  octoprint.plugin.StartupPlugin,
				  octoprint.plugin.SimpleApiPlugin,
				  octoprint.plugin.EventHandlerPlugin):

	##~~ SettingsPlugin mixin

	def get_settings_defaults(self):
		return dict(
			hue_token = None,
			hue_ip = None,
			light_id = None,
			auto_off = False,
			auto_off_type = 'direct',
			auto_off_bed_temp = 60,
			auto_off_nozzle_temp = 50,
			auto_connect = False,
			security_connection_lost = False,
			security_emergency_stop = True,
			security_nozzle_temp = 250,
			security_bed_temp = 80
		)

	def on_after_startup(self):
		self._logger.info("Hue IP: %s" % self._settings.get(['hue_ip']))
		#self._settings.set(['hue_token'], None)
		self.loopTemp = RepeatedTimer(5, self.checkSecurityTemp)
		self.loopTemp.start()

	def checkSecurityTemp(self):
		try:
			nozzle_temp = self._printer.get_current_temperatures()['tool0']['actual']
			bed_temp = self._printer.get_current_temperatures()['bed']['actual']
		except:
			pass
		else:	
			if(nozzle_temp >= int(self._settings.get(['security_nozzle_temp'])) or bed_temp >= int(self._settings.get(['security_bed_temp']))):
				requests.put("http://{}/api/{}/lights/{}/state".format(self._settings.get(['hue_ip']), self._settings.get(['hue_token']), self._settings.get(['light_id'])), json={"on": False})

	def get_template_vars(self):
		return dict(
			auto_off=self._settings.get(["auto_off"]),
			auto_off_bed_temp=self._settings.get(["auto_off_bed_temp"]),
			auto_off_nozzle_temp=self._settings.get(["auto_off_nozzle_temp"]),
			auto_connect=self._settings.get(['auto_connect'])
		)

	def get_template_configs(self):
		return [
			dict(type="navbar", custom_bindings=False),
			dict(type="settings", custom_bindings=False)
		]

	### API ###
	def get_api_commands(self):
		return dict(
			command1=[],
			pairing=['ip'],
			changeip=['ip'],
			configuration=['device_id'],
			updaterules=['rules']
		)

	def on_api_command(self, command, data):
		if command == "command1":
			return flask.jsonify(reponse="pas de command")
		elif command == "pairing":
			ip = data['ip']
			r = requests.post("http://{}/api".format(ip), json={"devicetype":"octoprint#ophom"})
			if(list(r.json()[0].keys())[0] == "error"):
				return flask.jsonify(reponse="error")
			elif(list(r.json()[0].keys())[0] == "success"):
				token = r.json()[0]['success']['username']
				self._settings.set(['hue_token'], token)
				self._settings.set(['hue_ip'], ip)
				self._settings.save()
				return flask.jsonify(reponse="success")
		elif command == "changeip":
			ip = data['ip']
			self._settings.set(['hue_ip'], ip)
			self._settings.save()
			return flask.jsonify(reponse="success")
		elif command == "configuration":
			self._settings.set(['light_id'], data['device_id'])
			self._settings.save()
			return flask.jsonify(reponse="success")
		elif command == "updaterules":
			# Fetch actual rules to get the id of the old one
			rules_list = requests.get("http://{}/api/{}/rules".format(self._settings.get(['hue_ip']), self._settings.get(['hue_token']))).json()

			id_on = None
			id_off = None

			for rule in rules_list:
				if(rules_list[rule]['name'] == "#ophom_on"):
					id_on = rule
				if(rules_list[rule]['name'] == "#ophom_off"):
					id_off = rule

			if(id_on != None):
				requests.delete("http://{}/api/{}/rules/{}".format(self._settings.get(['hue_ip']), self._settings.get(['hue_token']), id_on))
			if(id_off != None):
				requests.delete("http://{}/api/{}/rules/{}".format(self._settings.get(['hue_ip']), self._settings.get(['hue_token']), id_off))

			if(len(data['rules']['on']) != 0):
				actions = []
				for rule in data['rules']['on']:
					if(rule['action'] == "On"):
						on = True
					elif(rule['action'] == "Off"):
						on = False

					actions.append({"address":"/lights/{}/state".format(rule['id']), "method":"PUT", "body":{"on":on}})

				data_request = {
					"name": "#ophom_on",
					"conditions": [
						{"address":"/lights/{}/state/on".format(self._settings.get(['light_id'])), "operator":"eq", "value":"true"}
					],
					"actions": actions
				}

				response = requests.post("http://{}/api/{}/rules".format(self._settings.get(['hue_ip']), self._settings.get(['hue_token'])), json=data_request)

				print(response.json())

			if(len(data['rules']['off']) != 0):
				actions = []
				for rule in data['rules']['off']:
					if(rule['action'] == "On"):
						on = True
					elif(rule['action'] == "Off"):
						on = False

					actions.append({"address":"/lights/{}/state".format(rule['id']), "method":"PUT", "body":{"on":on}})

				data_request = {
					"name": "#ophom_off",
					"conditions": [
						{"address":"/lights/{}/state/on".format(self._settings.get(['light_id'])), "operator":"eq", "value":"false"}
					],
					"actions": actions
				}
				
				requests.post("http://{}/api/{}/rules".format(self._settings.get(['hue_ip']), self._settings.get(['hue_token'])), json=data_request)

			return flask.jsonify(reponse="success")



	# Requete API get
	def on_api_get(self, request):
		option = request.args.get('action')
		if(option == "discover"):
			r = requests.get("https://discovery.meethue.com/")
			return flask.jsonify(r.json())
		elif(option == "isconfigured"):
			token = self._settings.get(['hue_token'])
			light = self._settings.get(['light_id'])
			if(token == None and light == None):
				return flask.jsonify(reponse=0)
			elif(token != None and light == None):
				return flask.jsonify(reponse=1)
			elif(token != None and light != None):
				try:
					r = requests.get("http://{}/api/{}/lights/{}".format(self._settings.get(['hue_ip']), self._settings.get(['hue_token']), self._settings.get(['light_id'])), timeout=3)
				except:
					return flask.jsonify(reponse=3)
				else:
					return flask.jsonify(reponse=2)
		elif(option == "checkplugstatus"):
			r = requests.get("http://{}/api/{}/lights/{}".format(self._settings.get(['hue_ip']), self._settings.get(['hue_token']), self._settings.get(['light_id'])))
			if(r.json()['state']['on']):
				return flask.jsonify(reponse=1)
			else:
				return flask.jsonify(reponse=0)
		elif(option == "pluglist"):
			r = requests.get("http://{}/api/{}/lights".format(self._settings.get(['hue_ip']), self._settings.get(['hue_token'])))
			plug_list = []
			for device in r.json():
				if(r.json()[device]['type'] == "On/Off plug-in unit"):
					plug_list.append([device, r.json()[device]['name']])
			return flask.jsonify(plug_list)
		elif(option == "extractconfig"):
			r = requests.get("http://{}/api/{}".format(self._settings.get(['hue_ip']), self._settings.get(['hue_token'])))
			return flask.jsonify(r.json())
		elif(option == "toggle"):
			r = requests.get("http://{}/api/{}/lights/{}".format(self._settings.get(['hue_ip']), self._settings.get(['hue_token']), self._settings.get(['light_id'])))
			if(r.json()['state']['on']):
				requests.put("http://{}/api/{}/lights/{}/state".format(self._settings.get(['hue_ip']), self._settings.get(['hue_token']), self._settings.get(['light_id'])), json={"on": False})
				return flask.jsonify(reponse=0)
			else:
				requests.put("http://{}/api/{}/lights/{}/state".format(self._settings.get(['hue_ip']), self._settings.get(['hue_token']), self._settings.get(['light_id'])), json={"on": True})
				return flask.jsonify(reponse=1)
		elif(option == 'getbridgerules'):
			liste_lamp = {}
			liste_regle = {}
			liste_regle['on'] = []
			liste_regle['off'] = []

			request_liste_lamp = requests.get("http://{}/api/{}/lights/".format(self._settings.get(['hue_ip']), self._settings.get(['hue_token']))).json()
			request_liste_regle = requests.get("http://{}/api/{}/rules/".format(self._settings.get(['hue_ip']), self._settings.get(['hue_token']))).json()

			for lamp in request_liste_lamp:
				if(lamp != self._settings.get(['light_id'])):
					liste_lamp[lamp] = request_liste_lamp[lamp]['name']

			liste_regle_on = []
			liste_regle_off = []
			for regle in request_liste_regle:
				if(request_liste_regle[regle]['name'] == "#ophom_on"):
					for action in request_liste_regle[regle]['actions']:
						id_lamp = re.search(r"\/lights\/(\d)\/state", action['address']).group(1)
						action_lamp = action['body']['on']
						liste_regle_on.append({"id": id_lamp, "action": action_lamp})
					liste_regle['on'] = liste_regle_on
				
				if(request_liste_regle[regle]['name'] == "#ophom_off"):
					for action in request_liste_regle[regle]['actions']:
						id_lamp = re.search(r"\/lights\/(\d)\/state", action['address']).group(1)
						action_lamp = action['body']['on']
						liste_regle_off.append({"id": id_lamp, "action": action_lamp})
					liste_regle["off"] = liste_regle_off

			return flask.jsonify({"lights": liste_lamp, "rules": liste_regle})
		else:
			return flask.jsonify(error="Invalid command")

	### Extinction automatique 
	def on_event(self, event, payload):
		if(event == "PrintDone"):
			if(self._settings.get(['auto_off']) == True):
				while(True):
					if(self._printer.get_current_temperatures()['tool0']['actual'] <= int(self._settings.get(['auto_off_nozzle_temp'])) and self._printer.get_current_temperatures()['bed']['actual'] <= int(self._settings.get(['auto_off_bed_temp']))):
						if(self._settings.get(['auto_off_type']) == 'direct'):
							requests.put("http://{}/api/{}/lights/{}/state".format(self._settings.get(['hue_ip']), self._settings.get(['hue_token']), self._settings.get(['light_id'])), json={"on": False})
							break
						elif(self._settings.get(['auto_off_type']) == 'delayed'):
							address = "/api/{}/lights/{}/state".format(self._settings.get(['hue_token']), self._settings.get(['light_id']))
							data = {
								"name": "Power Off Printer",
								"description": "Automatic shutdown initiate by OctoPrint",
								"command": {
									"address": address,
									"body": {
										"on": False
									},
									"method": "PUT"
								},
								"time": "PT00:02:00"
							}
							requests.post("http://{}/api/{}/schedules/".format(self._settings.get(['hue_ip']), self._settings.get(['hue_token'])), json=data)
							import os
							shutdown_command = self._settings.global_get(["server", "commands", "systemShutdownCommand"])
							os.system(shutdown_command)
							break
					else:
						time.sleep(5)
		elif(event == "EStop"):
			if(self._settings.get(['security_emergency_stop']) == True):
				requests.put("http://{}/api/{}/lights/{}/state".format(self._settings.get(['hue_ip']), self._settings.get(['hue_token']), self._settings.get(['light_id'])), json={"on": False})
		elif(event == "Disconnected"):
			if(self._settings.get(['security_connection_lost']) == True):
				requests.put("http://{}/api/{}/lights/{}/state".format(self._settings.get(['hue_ip']), self._settings.get(['hue_token']), self._settings.get(['light_id'])), json={"on": False})


	##~~ AssetPlugin mixin

	def get_assets(self):
		# Define your plugin's asset files to automatically include in the
		# core UI here.
		return dict(
			js=["js/ophom.js"],
			css=["css/ophom.css"],
			less=["less/ophom.less"],
			hue_pairing=['images/hue_pairing.png']
		)


	##~~ Softwareupdate hook

	def get_update_information(self):
		# Define the configuration for your plugin to use with the Software Update
		# Plugin here. See https://docs.octoprint.org/en/master/bundledplugins/softwareupdate.html
		# for details.
		return dict(
			ophom=dict(
				displayName="Ophom Plugin",
				displayVersion=self._plugin_version,

				# version check: github repository
				type="github_release",
				user="Salamafet",
				repo="ophom",
				current=self._plugin_version,

				# update method: pip
				pip="https://github.com/Salamafet/ophom/archive/{target_version}.zip"
			)
		)


# If you want your plugin to be registered within OctoPrint under a different name than what you defined in setup.py
# ("OctoPrint-PluginSkeleton"), you may define that here. Same goes for the other metadata derived from setup.py that
# can be overwritten via __plugin_xyz__ control properties. See the documentation for that.
__plugin_name__ = "Ophom"

# Starting with OctoPrint 1.4.0 OctoPrint will also support to run under Python 3 in addition to the deprecated
# Python 2. New plugins should make sure to run under both versions for now. Uncomment one of the following
# compatibility flags according to what Python versions your plugin supports!
#__plugin_pythoncompat__ = ">=2.7,<3" # only python 2
#__plugin_pythoncompat__ = ">=3,<4" # only python 3
__plugin_pythoncompat__ = ">=2.7,<4" # python 2 and 3

def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = OphomPlugin()

	global __plugin_hooks__
	__plugin_hooks__ = {
		"octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
	}

