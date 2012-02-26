# Auto-generated config for <%= name %>

lxc.utsname = <%= name %>

lxc.tty = 4
lxc.pts = 1024
lxc.rootfs = /mnt/vm0/rootfs
lxc.mount = /mnt/<%= name %>/fstab
lxc.network.type = veth
lxc.network.flags = up
lxc.network.name = eth0
lxc.network.link = br0
lxc.network.ipv4 = <%= ip %>
 
lxc.cgroup.devices.deny = a

lxc.cgroup.memory.limit_in_bytes = 256M

# /dev/null and zero
lxc.cgroup.devices.allow = c 1:3 rwm
lxc.cgroup.devices.allow = c 1:5 rwm
# consoles
#lxc.cgroup.devices.allow = c 5:1 rwm
#lxc.cgroup.devices.allow = c 5:0 rwm
#lxc.cgroup.devices.allow = c 4:0 rwm
#lxc.cgroup.devices.allow = c 4:1 rwm
# /dev/{,u}random
lxc.cgroup.devices.allow = c 1:9 rwm
lxc.cgroup.devices.allow = c 1:8 rwm
lxc.cgroup.devices.allow = c 136:* rwm
lxc.cgroup.devices.allow = c 5:2 rwm
# rtc
lxc.cgroup.devices.allow = c 254:0 rwm