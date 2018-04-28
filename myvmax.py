import os
import subprocess
p=subprocess.call(['symcfg','list'])
print(p)
print("====================================================================================")
#q=subprocess.call(['symacess','-sid','1281','list','view'])
#print(q)
q=os.system('symcfg -sid 1281 list -fa all >> bc.txt')
print(q)

#f= open("vmaxdc2.txt","w+")
#f= open("guru99.txt","a")
#f.write("This is line aaaa".join(p))
#f.close()
f= open("abc.txt","r")
x=f.readlines()
for y in x:
	print(y)

	
