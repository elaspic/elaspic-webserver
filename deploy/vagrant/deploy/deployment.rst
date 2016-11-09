Deploying Vagrant Boxes to Xen
==============================

Set Variables
--------------

Set the environmental variables that we will be using::

    HOST_NAME='elaspic'
    HOST_IP='192.168.6.53'    
    BOX_FILENAME=/home/strokach/virtualbox/mum_default_1441915165550_76503/packer-virtualbox-iso-1441852233-disk1.vmdk


Modify the Image
----------------

Clone the virtual machine into a RAW format::

    vboxmanage clonemedium ${BOX_FILENAME} ${BOX_FILENAME%.*}.img --format RAW

Mount the image so we can make some changes::

    sudo mkdir /mnt/myimg
    sudo fdisk -l ${BOX_FILENAME%.*}.img
    sudo mount -o loop,offset=$((2048 * 512)) ${BOX_FILENAME%.*}.img /mnt/myimg

Copy the `./interfaces` file which contains the new ``eth0`` bridged interface (instead of the NAT interface used by Vagrant)::
    
    sudo cp -v /mnt/myimg/etc/network/interfaces{,.bak}
    sudo cp -v ./interfaces /mnt/myimg/etc/network/interfaces
    
Revert to the original `/etc/sudoers` file where users get prompted for password when using ``sudo``::

    sudo cp -v /mnt/myimg/etc/sudoers{.orig,}

Change the hostname and hosts::

    echo "$HOST_NAME" | sudo tee /mnt/myimg/etc/hostname
    sudo sed -i "s@127.0.1.1\tkimadmin-vm@${HOST_IP}\t${HOST_NAME}.kimlab.med.utoronto.ca ${HOST_NAME}.org ${HOST_NAME}@g" /mnt/myimg/etc/hosts  
    # Change mum.settings if you are modifying HOST_IP from default    

Unmount the image::

    sudo umount /mnt/myimg

Copy the image to a folder used by Xen::

    sudo cp -v ${BOX_FILENAME%.*}.img /home/kimlab3/vm_images/elaspic_v2/domains/elaspic.kimlab.med.utoronto.ca/
    

Modify the Xen Guest
--------------------

Boot the VM using Xen, and log in using SSH.

Change passwords::

    sudo passwd
    sudo passwd kimadmin

Install kernel modules::

    umask -a 
    sudo apt-get install linux-image-3.13.0-39-generic # replace the version with what ``umask`` tells you
    sudo mount --all

I don't know why, but the kernel version changes when you boot the VM using Xen!!!

