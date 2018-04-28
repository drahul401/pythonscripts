import subprocess
import shlex

outputfile = open('symfaout.txt', 'w')
command = 'symcfg -sid 1281 list -v -fa all -output xml_e'
command = shlex.split(command)
p = subprocess.call(command, stdout=outputfile)



