import subprocess
out = subprocess.check_output(['arp', '-a']).decode('utf-8')
print(out.split('\n')[:5])
