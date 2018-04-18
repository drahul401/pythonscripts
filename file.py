Python 3.5.4 (v3.5.4:3f56838, Aug  8 2017, 02:17:05) [MSC v.1900 64 bit (AMD64)] on win32
Type "copyright", "credits" or "license()" for more information.
>>> 
>>> 
>>> f=open("C:\Users\AJAY\Desktop\python","w")
SyntaxError: (unicode error) 'unicodeescape' codec can't decode bytes in position 2-3: truncated \UXXXXXXXX escape
>>> 
>>> f=open("C:\\Users\\AJAY\\Desktop\\python\\rd.txt","w")
>>> f.write("RD is king")
10
>>> f.close()
>>> 
