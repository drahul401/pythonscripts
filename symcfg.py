import subprocess
import shlex

symcfg_command = 'symcfg list'
symcfg_command = shlex.split(symcfg_command)
p = subprocess.Popen(symcfg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
symcfg_out, stderr = p.communicate()
print symcfg_out 

symaccess_command = 'symaccess -sid 1281 list view'
symaccess_command = shlex.split(symaccess_command)
p = subprocess.Popen(symcfg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
symaccess_out, stderr = p.communicate()
print symaccess_out 

print "-"*100
def run_command(command):
	command = shlex.split(command)
	p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
	stdout,stderr = p.communicate()
	return {'stdout': stdout, 'stderr': stderr, 'returncode': p.returncode}

symcfg_out = run_command('symcfg list')
symaccess_out = run_command('symaccess -sid 1281 list view')
print symcfg_out, symaccess_out
