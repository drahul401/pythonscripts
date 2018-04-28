
##f= open("C:\\users\\dandamur\\Desktop\\symcfg_out.txt","r")
##x=f.readlines()
##n=str(input("Dev name: "))
##for y in x:
##        if n in y :
##                print(y)
##f.close()

import time
start_time = time.time()




f= open('C:\\users\\dandamur\\Desktop\\alldev.txt')
n=str(input("dev name: "))

for y in f:
	if n in y:
		print(y.strip())
print("--- %s seconds ---" % (time.time() - start_time))
