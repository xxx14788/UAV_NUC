=== A.1 forensic summary 2026-10-17 01:1x ===
① dpkg -V full-lib: 46 lines, 0 gazebo/ogre/mesa/glvnd/nvidia/ros-noetic hits; flagged items = /tmp ros-foxy build leftovers(no md5) + /boot+sudoers permission-denied(benign) + mavros px4.launch??5 + rosdep sources_list??5; blind spot = conffiles/md5sums-absent files not verifiable
② ld.so shadow audit: ld.so.conf.d only standard multiarch+fakeroot+libc; OGRE 1.9.0 all /lib/x86_64-linux-gnu; GL via glvnd standard; /usr/local/lib has only libceres.a/cmake/python => NO shadow libs
③ dpkg.status.0 (10-12 23:14) vs current: render-chain 120 pkgs, VERSION-DIFF=0 => no rollback candidate => A.3 shotgun reinstall path
