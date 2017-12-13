#!/usr/bin/env python

from __future__ import print_function
import argparse
import digitalocean
import os
import uuid
import paramiko
import time

parser = argparse.ArgumentParser(description='Build Android on DigitalOcean')
parser.add_argument('token', type=str, help="DO authentication token")
parser.add_argument('-v', '--volume_id', dest='volume_id', help="DO volume to use. Leave blank to add a new volume", default=None)
parser.add_argument('-d', '--droplet_id', dest='droplet_id', help="DO droplet to use. Leave blank to add a new droplet", default=None)
parser.add_argument('--droplet_size', dest='droplet_size', default='512mb', help="Name of the droplet size to use")
parser.add_argument('--show_choices', default=False, type=bool)

args = parser.parse_args()
token = args.token

# Currently the most powerful machine available for me.
# Fetching source:  8min download + 8min unpacking
# Compiling:        ~40 min?
# TODO switch to high-cpu with 4 or 8 dedicated cores once it is unlocked
size_slug = '8gb'

print("Using token: {}".format(token))

manager = digitalocean.Manager(token=token)

if args.show_choices:
    print("Images: ")
    for item in manager.get_images():
        print(item.slug)

    print()
    print("Sizes: ")
    for item in manager.get_all_sizes():
        if item.available:
            print("{} - {}/hr; RAM={}; vCPU={}".format(item.slug, item.price_hourly, item.memory, item.vcpus))
   
    exit()

# Generate temporary key
def get_ssh_key(fingerprint):
    print("Looking for " + fingerprint)
    for fname in os.listdir(".ssh_keys"):
        if not (".pub" in fname):
            if fingerprint in os.popen("ssh-keygen -E md5 -lf .ssh_keys/" + fname).read():
                print("Found " + fname)
                return fname

    return None
    
fname = str(uuid.uuid4())
os.system("mkdir -p .ssh_keys")

key = None
for item in manager.get_all_sshkeys():
    if get_ssh_key(item.fingerprint) != None:
        key = item
        break

if key == None:
    os.system("ssh-keygen -f .ssh_keys/" + fname + " -N ''")
    ssh_key = open(".ssh_keys/" + fname + ".pub").read()
    key = digitalocean.SSHKey(token=token,
            name='temp-key',
            public_key=ssh_key)
    key.create()

# Create / load volume
if True:
    if args.volume_id == None:
        volume = digitalocean.Volume(token=token,
                size_gigabytes=150,
                name='abv',
                region='fra1')
        volume.create()
    else:
        print("Using existing volume.")
        volume = manager.get_volume(args.volume_id)
else:
    volume = None

print("Volume ID: {}".format(volume.id))

# Create / load droplet
if args.droplet_id == None:
    if volume == None:
        volumes = []
    else:
        volumes = [ volume.id ]

    droplet = digitalocean.Droplet(token=token,
                                   name='android-build-droplet',
                                   region='fra1',
                                   image='ubuntu-16-04-x64', # Ubuntu 16.04 x64
                                   size_slug=size_slug,
                                   volumes=volumes,
                                   ssh_keys=[ key ],
                                   backups=False)
    droplet.create()
else:
    print("Using existing droplet.")
    droplet = manager.get_droplet(args.droplet_id)

time.sleep(15)

droplet = manager.get_droplet(args.droplet_id)

# key = droplet.ssh_keys[0]
print("Droplet ID: {}".format(droplet.id))
ip = droplet.networks['v4'][0]['ip_address']
print("Droplet IP: {}".format(ip))

fingerprint=key.fingerprint #'b9:26:3b:a9:48:e2:40:8f:68:cd:81:ec:d9:0a:29:db'# key.fingerprint

key_filename = ".ssh_keys/" + get_ssh_key(fingerprint)
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(ip, username='root', key_filename=key_filename)

def run(client, command):
    result = ""
    print("Running " + command)
    stdin, stdout, stderr = client.exec_command(command)
    for line in stdout:
        print(line.strip('\n'))
        result += line

    for line in stderr:
        print(line.strip('\n'))

run(client, "bash -c 'apt-get update && apt-get install git build-essential libncurses5-dev bzip2 python repo default-jdk imagemagick schedtool git-core gnupg flex bison gperf build-essential zip curl zlib1g-dev gcc-multilib g++-multilib libc6-dev-i386 lib32ncurses5-dev x11proto-core-dev libx11-dev lib32z-dev ccache libgl1-mesa-dev libxml2-utils xsltproc unzip -y --force-yes'")

if volume == None:
    run(client, "bash -c 'sudo mkdir -p /mnt/volume'")
else:
    volume_path = "scsi-0DO_Volume_" + volume.name

    run(client, "bash -c 'if ! mount | grep volume; then sudo mkfs.ext4 -F /dev/disk/by-id/" + volume_path + "; sudo mkdir -p /mnt/volume; sudo mount -o discard,defaults /dev/disk/by-id/" + volume_path + " /mnt/volume; fi'")

    run(client, "bash -c 'cd /mnt/volume; if [ ! -d /mnt/volume/.repo ]; then repo init --depth=1 -u https://github.com/Jos635/android -b cm-14.1; fi'")

run(client, "bash -c 'cd /mnt/volume/.repo/manifests; git pull'")
run(client, "bash -c 'cd /mnt/volume; repo sync'")
run(client, "bash -c 'cd /mnt/volume; buildscripts/make-build.sh'")

sftp = client.open_sftp()
sftp.chdir("/mnt/volume/")

os.system("mkdir -p output")

for remotefile in sftp.listdir():
    if ".zip" in remotefile:
        print("Downloading " + remotefile)
        shutil.copyfileobj(sftp.open("./" + remotefile), open("output/" + remotefile), 16384)

client.close()

# destroy droplet iff not specified by argument
if args.droplet_id == None:
    droplet.destroy()

# destroy volume iff not specified by argument
if args.volume_id == None:
    volume.destroy()

# let the user know what's left, to prevent surprises
print("Droplets left:")
print(manager.get_all_droplets())

print("Volumes left:")
print(manager.get_all_volumes())
