#
# fullbuild creates everything that needs to be created before a
# distribution can be made, and puts it all in the right place.
#
# It expects the projects to be in the places where Jack likes them:
# in directories named like 'build.mac'. That is fixable,
# however.
#
# NOTE: You should proably make a copy of python with which to execute this
# script, rebuilding running programs does not work...

MACBUILDNO=":Mac:Include:macbuildno.h"

import os
import sys
import macfs
import MacOS
import EasyDialogs
import regex
import string

import aetools
import AppleEvents
from Metrowerks_Shell_Suite import Metrowerks_Shell_Suite
from CodeWarrior_Standard_Suite import CodeWarrior_Standard_Suite
from Required_Suite import Required_Suite

import Res
import Dlg

import buildtools
import cfmfile

# Dialog resource. Note that the item numbers should correspond
# to those in the DITL resource. Also note that the order is important:
# things are built in this order, so there should be no forward dependencies.
DIALOG_ID = 512

I_OK=1
I_CANCEL=2
I_INC_BUILDNO=19

I_CORE=3
I_PPC_PLUGINS=4
I_PPC_EXTENSIONS=5
I_68K_PLUGINS=6
I_68K_EXTENSIONS=7
I_PPC_FULL=8
I_PPC_SMALL=9
I_68K_FULL=10
I_68K_SMALL=11
I_APPLETS=12

N_BUTTONS=13

class MwShell(Metrowerks_Shell_Suite, CodeWarrior_Standard_Suite,
				Required_Suite, aetools.TalkTo):
	pass

RUNNING=[]

def buildmwproject(top, creator, projects):
	"""Build projects with an MW compiler"""
	mgr = MwShell(creator, start=1)
	mgr.send_timeout = AppleEvents.kNoTimeOut
	
	for file in projects:
		if type(file) == type(()):
			file, target = file
		else:
			target = ''
		file = os.path.join(top, file)
		try:
			fss = macfs.FSSpec(file)
		except ValueError:
			print '** file not found:', file
			continue
		print 'Building', file, target
		try:
			mgr.open(fss)
		except aetools.Error, detail:
			print '**', detail, file
			continue
		if target:
			try:
				mgr.Set_Current_Target(target)
			except aetools.Error, arg:
				print '**', file, target, 'Cannot select:', arg
		try:
			mgr.Make_Project()
		except aetools.Error, arg:
			print '**', file, target, 'Failed:', arg
		mgr.Close_Project()
##	mgr.quit()
	
def buildapplet(top, dummy, list):
	"""Create python applets"""
	template = buildtools.findtemplate()
	for src, dst in list:
		if src[-3:] != '.py':
			raise 'Should end in .py', src
		base = os.path.basename(src)
		#dst = os.path.join(top, base)[:-3]
		src = os.path.join(top, src)
		dst = os.path.join(top, dst)
		try:
			os.unlink(dst)
		except os.error:
			pass
		print 'Building applet', dst
		buildtools.process(template, src, dst, 1)
		
def buildfat(top, dummy, list):
	"""Build fat binaries"""
	for dst, src1, src2 in list:
		dst = os.path.join(top, dst)
		src1 = os.path.join(top, src1)
		src2 = os.path.join(top, src2)
		print 'Building fat binary', dst
		cfmfile.mergecfmfiles((src1, src2), dst)
		
def handle_dialog(filename):
	"""Handle selection dialog, return list of selected items"""
	d = Dlg.GetNewDialog(DIALOG_ID, -1)
	d.SetDialogDefaultItem(I_OK)
	d.SetDialogCancelItem(I_CANCEL)
	results = [0]*N_BUTTONS
	while 1:
		n = Dlg.ModalDialog(None)
		if n == I_OK:
			break
		if n == I_CANCEL:
			return []
		if n == I_INC_BUILDNO:
			incbuildno(filename)
			continue
		if n < len(results):
			results[n] = (not results[n])
			tp, h, rect = d.GetDialogItem(n)
			h.as_Control().SetControlValue(results[n])
	rv = []
	for i in range(len(results)):
		if results[i]:
			rv.append(i)
	return rv

#
# The build instructions. Entries are (routine, arg, list-of-files)
# XXXX We could also include the builds for stdwin and such here...
BUILD_DICT = {
I_CORE : (buildmwproject, "CWIE", [
		(":Mac:Build:PythonCore.prj", "PythonCore"),
		(":Mac:Build:Python.prj", "PythonFAT"),
		(":Mac:Build:PythonApplet.prj", "PythonAppletFAT"),
	]),

I_PPC_PLUGINS : (buildmwproject, "CWIE", [
		(":Mac:Build:PlugIns.prj",	"PlugIns.ppc"),
	]),

I_68K_PLUGINS : (buildmwproject, "CWIE", [
		(":Mac:Build:PlugIns.prj",	"PlugIns.CFM68K"),
	]),

I_68K_FULL : (buildmwproject, "CWIE", [
		(":Mac:Build:PythonStandalone.prj", "Python68K"),
	]),
	
I_68K_SMALL : (buildmwproject, "CWIE", [
		(":Mac:Build:PythonStandSmall.prj", "PythonSmall68K"),
	]),

I_PPC_FULL : (buildmwproject, "CWIE", [
		(":Mac:Build:PythonStandalone.prj", "PythonStandalone"),
	]),

I_PPC_SMALL : (buildmwproject, "CWIE", [
		(":Mac:Build:PythonStandSmall.prj", "PythonStandSmall"),
	]),

I_PPC_EXTENSIONS : (buildmwproject, "CWIE", [
		(":Extensions:Imaging:_imaging.prj", "_imaging.ppc"),
		(":Extensions:Imaging:_tkinter.prj", "_tkinter.ppc"),
		(":Extensions:NumPy:numpymodules.prj", "numpymodules.ppc"),
	]),

I_68K_EXTENSIONS : (buildmwproject, "CWIE", [
		(":Extensions:Imaging:_imaging.prj", "_imaging.CFM68K"),
		(":Extensions:Imaging:_tkinter.prj", "_tkinter.CFM68K"),
		(":Extensions:NumPy:numpymodules.prj", "numpymodules.CFM68K"),
	]),

I_APPLETS : (buildapplet, None, [
		(":Mac:scripts:EditPythonPrefs.py", "EditPythonPrefs"),
		(":Mac:scripts:BuildApplet.py", "BuildApplet"),
		(":Mac:scripts:BuildApplication.py", "BuildApplication"),
		(":Mac:scripts:ConfigurePython.py", "ConfigurePython"),
		(":Mac:Tools:IDE:PythonIDE.py", "Python IDE"),
	]),
}

def incbuildno(filename):
	fp = open(filename)
	line = fp.readline()
	fp.close()
	
	pat = regex.compile('#define BUILD \([0-9][0-9]*\)')
	pat.match(line)
	buildno = pat.group(1)
	if not buildno:
		raise 'Incorrect macbuildno.h line', line
	new = string.atoi(buildno) + 1
	fp = open(filename, 'w')
	fp.write('#define BUILD %d\n'%new)
	fp.close()
				
def main():
	try:
		h = Res.OpenResFile('fullbuild.rsrc')
	except Res.Error:
		pass	# Assume we already have acces to our own resource

	dir, ok = macfs.GetDirectory('Python source folder:')
	if not ok:
		sys.exit(0)
	dir = dir.as_pathname()
	
	todo = handle_dialog(os.path.join(dir, MACBUILDNO))
		
	instructions = []
	for i in todo:
		instructions.append(BUILD_DICT[i])
		
	for routine, arg, list in instructions:
		routine(dir, arg, list)
		
	print "All done!"
	sys.exit(1)	
	
if __name__ == '__main__':
	main()
	
