proc            /mnt/vm0/rootfs/proc         proc    nodev,noexec,nosuid 0 0
devpts          /mnt/vm0/rootfs/dev/pts      devpts defaults 0 0
sysfs           /mnt/vm0/rootfs/sys          sysfs defaults  0 0
/var/www/scraperwiki/services/scriptmgr/scripts /mnt/vm0/rootfs/home/startup bind defaults,bind,ro 0 0
/var/www/scraperwiki/scraperlibs/ /mnt/vm0/rootfs/home/scraperwiki bind defaults,bind,ro 0 0
/usr/lib/lxc /mnt/vm0/rootfs/usr/lib/lxc bind defaults,bind,ro 0 0
/mnt/<%= name %>/code/ /mnt/vm0/rootfs/home/scriptrunner bind defaults,bind 0 0
/mnt/<%= name %>/code/ /mnt/vm0/rootfs/tmp bind defaults,bind 0 0

#/var/www/scraperwiki/resourcedir/<%= scrapername %>/ /mnt/vm0/rootfs/tmp bind defaults,bind 0 0
