input_file = open('mv.txt')

input_Server_name = raw_input("Enter Server Name: ").strip()
for line in input_file:
	if input_Server_name in line:
		print(line)
		#break
	else:
		continue

		