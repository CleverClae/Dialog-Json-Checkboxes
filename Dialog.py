#!/usr/bin/python3

import json
import os
import time
import subprocess

# set to false to generate an intermediate json file
# set to true to pass generated json in as a string
stringinput = True
DIALOG = "/usr/local/bin/dialog" 
DIALOG_COMMAND_FILE = "/var/tmp/dialog.log"
Icons=""
dialog_app = "/Library/Application Support/Dialog/Dialog.app/Contents/MacOS/Dialog"

jamfcmd = [
        "usr/local/bin/jamf policy",
        "-trigger",
    ]

def Jamf_Command():
    "Install app"
    

    
optional_apps = {"label" : "Atom", "checked" : "false"},\
	  		{"label" : "Sublime Txt", "checked" : "false"},\
	  		{"label" : "BBedit", "checked" : "false"},\
	  		{"label" : "VSCode", "checked" : "false"}, \
	  		{"label" : "Microsoft Remote Desktop", "checked" : "false"}, \
	  		{"label" : "Apple Remote Desktop", "checked" : "false"}

def update_dialog(command, value=""):
    """Updates the current dialog window"""
    with open(DIALOG_COMMAND_FILE, "a") as log:
        log.write(f"{command}: {value}\n")

class DialogAlert:
    def __init__(self):
        # set the default look of the alert
        self.content_dict = {
            "alignment": "center",
            "button1text": "Continue",
            "centericon": 1,
            "icon": "SF=laptopcomputer.and.arrow.down",
            "iconsize": "500",
            "message": (
                f"## The IT notification system has experienced an error.\n\n"
                "Please log a ticket with [{TICKET_TEXT}]({TICKET_LINK})"
            ),
            "messagefont": "size=16",
            "title": "none",
        }
        self.app_install_dict = {
            "alignment": "left",
            "button1text": "Please Wait",
            "hidetimerbar": True,
            "icon": "/System/Library/CoreServices/Installer.app",
            "iconsize": "250",
            "message": (
                f"## The IT notification system has experienced an error.\n\n"
                "Please log a ticket with [{TICKET_TEXT}]({TICKET_LINK})"
            ),
            "messagefont": "size=16",
            "title": "Setting up your Mac",
        }

    def alert(self, contentDict, background=False):
        """Runs the SwiftDialog app and returns the exit code"""
        jsonString = json.dumps(contentDict)
        cmd = [DIALOG, "-o", "--jsonstring", jsonString, "--json"]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if background:
            return proc
        (out, err) = proc.communicate(input)
        result_dict = {
            "stdout": out,
            "stderr": err,
            "status": proc.returncode,
            "success": True if proc.returncode == 0 else False,
        }
        return result_dict

    def install_apps(self, app_dict):
        i = 1
        for app, options in app_dict.items():
            jamfname = options.get("jamf_name", app)
            app_name = options.get("name_on_disk", app)
            app_location = options.get("app_location", f"/Applications/{app_name}.app")
            icon = options.get("icon", f"{Icons}{jamfname}.png")
            time.sleep(1)
            update_dialog("progress", i)
            update_dialog("icon", icon)
            update_dialog("progresstext", f"Installing {app}")
            update_dialog(
                "listitem", f"title: {app}, status: wait, statustext: Installing"
            )
            i += 1
            time.sleep(2)
            while not os.path.exists(app_location):
                write_log(f"Waiting for {app} to install.")
                time.sleep(1)
            update_dialog(
                "listitem", f"title: {app}, status: success, statustext: Installed"
            )
            update_dialog("progress", i)
            update_dialog("progresstext", f"{app} installed.")
            time.sleep(1)
            i += 1
           

contentDict = {"title" : " IPG Health", 
            "titlefont" : "name=Arial,colour=#3FD0a2,size=40",
            "message" : "This is a **very important** messsage and you _should_ read it carefully\n\nThis is on a new line",
            "icon" : "/Library/Application Support/JAMF/Jamf.app/Contents/Resources/AppIcon.icns",
            "background" : "/Library/Application Support/IPG/image.png",
            "hideicon" : 0,
            "infobutton" : 1,
            "quitoninfo" : 1,
            "checkbox" : optional_apps
}
	

jsonString = json.dumps(contentDict)

if stringinput:
    print("Using string Input")
    os.system("'{}' --jsonstring '{}'".format(dialog_app, jsonString))
    apps_to_check = []

    for app in optional_apps:
        apps_to_check.append({"label": app, "checked": optional_apps[app]["default"]})
    app_chooser = DialogAlert()
    app_chooser.app_install_dict["button1text"] = "Continue"
    app_chooser.app_install_dict["timer"] = "600"
    app_chooser.app_install_dict["messagefont"] = "size=12"
    app_chooser.app_install_dict["checkbox"] = apps_to_check
    app_chooser.app_install_dict["message"] = (
        "## Please select the basic apps to install:\n\n"
        "Unsure of what to choose? Leave the defaults and install additional software later."
    )
    write_log("Alert for optional software")
    results = app_chooser.alert(app_chooser.app_install_dict)
    # Dialog is currently piping some internal errors to stdout when run as a root launchd
    # This is a workaround to strip those errors from the output of the checkbox selection
    # Once the results["stdout"] returns valid json, we could remove the workaround.
    write_log(f"Subprocess results: {results}")
    stdout = results["stdout"].decode("utf-8")
    stdout_json = stdout[stdout.index("{") :]
    write_log(f"Subprocess stdout cleaned: {json.loads(stdout_json)}")
    choosen_apps = {}
    if results["status"] == 0:
        write_log("User has selected continue")
        choosen_apps = json.loads(stdout_json)
    # Timer set for 10 minutes, if user doesn't select, we will install the defaults.
    elif results["status"] == 4:
        write_log("User has reached the timeout, moving on with defaults.")
        for app in optional_apps:
            if optional_apps[app]["default"]:
                choosen_apps[app] = True

    apps_to_install = {}
    for app, result in choosen_apps.items():
        if result:
            apps_to_install[app] = optional_apps[app]

    if apps_to_install:
        message = "Installing the selected applications:"
        write_log("Updating the self service manifest")
        update_self_service_manifest(apps_to_install)
        threading.Thread(target=run_munki).start()
        process_apps_to_install(apps_to_install, message)


    else:
        print("Using file Input")
    
    
    # create a temporary file
    jsonTMPFile = "/tmp/dialog.json"
    f = open(jsonTMPFile, "w")
    f.write(jsonString)
    f.close()
    


    os.system("'{}' --jsonfile {}".format(dialog_app, jsonTMPFile))

    # clean up
    os.remove(jsonTMPFile)