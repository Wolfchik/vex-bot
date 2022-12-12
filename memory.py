class Memory:
	def write(name, value):
		with open(name, "w") as file:
			file.write(str(value))

	def read(name):
		with open(name, "r") as file:
			text = file.read()
			return text