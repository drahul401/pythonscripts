import subprocess
import shlex
symcfg_outfile = open('symcfg_outfile.txt', 'w')
symcfg_command = 'symcfg list'
symcfg_command = shlex.split(symcfg_command)
p = subprocess.call(symcfg_command, stdout=symcfg_outfile)
f= open('symcfg_outfile.txt')
n=str(input("server name: "))

for y in f:
	if n in y:
		print(y.strip())
