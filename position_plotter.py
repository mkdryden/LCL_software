import matplotlib.pyplot as plt

f = r'C:\Users\Wheeler\Desktop\LCL_software\Experiments\experiment_16_05_2018___10.09.18.351281\experiment_16_05_2018___10.09.18.351281.log'

with open(f,'rb') as f:
	lines = f.readlines()

lines = [str(line,'utf-8') for line in lines]

xs = []
ys = []

for line in lines:
	if 'position during qswitch' in line:
		print(line)
		x = line.split(',')[0].split("'")[1]
		y = line.split(',')[1].split(',')[-1]
		print(x,y)
		xs.append(int(x))
		ys.append(int(y))

print(len(xs))
for i in xs:
	print(i)
plt.scatter(xs,ys)
plt.show()
