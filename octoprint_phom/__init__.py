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
import flask
import requests

class OphomPlugin(octoprint.plugin.SettingsPlugin,
                  octoprint.plugin.AssetPlugin,
                  octoprint.plugin.TemplatePlugin,
				  octoprint.plugin.StartupPlugin,
				  octoprint.plugin.SimpleApiPlugin):

	##~~ SettingsPlugin mixin

	def get_settings_defaults(self):
		return dict(
			hue_token = None,
			hue_ip = None,
			hue_configured = False,
			light_id = None,
			auto_off = False,
			auto_off_bed_temp = 60,
			auto_off_nozzle_temp = 60,
			light_status = 0
		)

	def on_after_startup(self):
		self._logger.info("Light Status: %s" % self._settings.get(['light_status']))
		#self._settings.set(['hue_token'], None)


	# def get_template_vars(self):
	# 	return dict(
	# 		hue_token=self._settings.get(["hue_token"]),
	# 		hue_ip=self._settings.get(["hue_ip"]),
	# 		hue_configured=self._settings.get(["hue_configured"]),
	# 		auto_off=self._settings.get(["auto_off"]),
	# 		auto_off_bed_temp=self._settings.get(["auto_off_bed_temp"]),
	# 		auto_off_nozzle_temp=self._settings.get(["auto_off_nozzle_temp"]),
	# 		light_status=self._settings.get(["light_status"])
	# 	)

	def get_template_configs(self):
		return [
			dict(type="navbar", custom_bindings=False),
			dict(type="settings", custom_bindings=False)
		]

	### API ###
	def get_api_commands(self):
		return dict(
			command1=[],
			pairing=['ip']
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
				return flask.jsonify(reponse="success")


	# Requete API get
	def on_api_get(self, request):
		option = request.args.get('action')
		if(option == "discover"):
			r = requests.get("https://discovery.meethue.com/")
			return flask.jsonify(r.json())
		elif(option == "isconfigured"):
			return flask.jsonify(reponse=self._settings.get(['hue_configured']))
		elif(option == "checkplugstatus"):
			return flask.jsonify(reponse=0)
		else:
			return flask.jsonify(error="Invalid command")

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
__plugin_pythoncompat__ = ">=3,<4" # only python 3
#__plugin_pythoncompat__ = ">=2.7,<4" # python 2 and 3

def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = OphomPlugin()

	global __plugin_hooks__
	__plugin_hooks__ = {
		"octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
	}

