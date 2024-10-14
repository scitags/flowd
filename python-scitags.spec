%define pypi_name scitags
%define version 1.1.6
%define release 3%{?dist}
%define _unpackaged_files_terminate_build 0

Name: python3-scitags
Version: 1.1.6
Release: %{release}
Summary: Scitags Flow and Packet Marking Service
Url: https://github.com/scitags/flowd
Source0: %{pypi_name}-%{version}.tar.gz
# Source0: https://files.pythonhosted.org/packages/source/f/%{pypi_name}/%{pypi_name}-%{version}.tar.gz
# Source1: %{url}/archive/refs/tags/v%{version}as.tar.gz
License: ASL 2.0
Group: Development/Libraries
Prefix: %{_prefix}
BuildArch: noarch
Obsoletes: python-flowd <= %{version}
BuildRequires: python3
BuildRequires: python3-setuptools
BuildRequires: python3-devel
BuildRequires: systemd-rpm-macros
Requires: python3-requests
Requires: python3-psutil 
Requires: systemd

%description

Flow and Packet Marking Service (flowd) implementation based on the Scitags specification (www.scitags.org).

%package prometheus
Summary:        Prometheus flowd backend
Group:          Development/Libraries
Requires:       python%{python3_pkgversion}-scitags
Requires:       python%{python3_pkgversion}-prometheus_client
Requires:       iproute

%description prometheus
This package adds Prometheus exporter for the network flows including detailed netlink information

%package netlink
Summary:        Netlink flowd plugin and backend
Group:          Development/Libraries
Requires:       python%{python3_pkgversion}-scitags
Requires:       python%{python3_pkgversion}-pyroute2
Requires:       iproute

%description netlink
This package adds netlink information to the network flows 

%package ebpf
Summary:        Packet marking backend for IPv6 flow label (uses eBPF) 
Group:          Development/Libraries
Requires:       python%{python3_pkgversion}-bcc

%description ebpf
This package adds packet marking capability on IPv6 flow label field using eBPF/BCC plugin.

%prep
%autosetup -n %{pypi_name}-%{version}
pathfix.py -pni "%{__python3} %{py3_shbang_opts}" . sbin/flowd

%build
%py3_build

%install
%py3_install

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root)
%doc README.md
%license LICENSE
%{python3_sitelib}/scitags/settings.py
#%{python3_sitelib}/scitags/__pycache__/settings.cpython-3X{,.opt-?}.pyc
%{python3_sitelib}/scitags/service.py
%{python3_sitelib}/scitags/__init__.py
%{python3_sitelib}/scitags/config.py
%{python3_sitelib}/scitags/stun/*
%{python3_sitelib}/scitags/plugins/firefly.py
%{python3_sitelib}/scitags/plugins/netstat.py
%{python3_sitelib}/scitags/plugins/__init__.py
%{python3_sitelib}/scitags/plugins/iperf.py
%{python3_sitelib}/scitags/plugins/np_api.py
%{python3_sitelib}/scitags/backends/udp_firefly.py
%{python3_sitelib}/scitags/backends/__init__.py
%{python3_sitelib}/scitags/netlink/__init__.py
%config(noreplace) /etc/flowd/flowd.cfg
%attr(755, root, root) /usr/sbin/flowd
/usr/lib/systemd/system/flowd.service

%files prometheus
%{python3_sitelib}/scitags/netlink/cache_ss.py
%{python3_sitelib}/scitags/backends/prometheus.py

%files netlink
%{python3_sitelib}/scitags/netlink/cache.py
%{python3_sitelib}/scitags/netlink/pyroute_tcp.py

%files ebpf
%{python3_sitelib}/scitags/backends/ebpf.py

%post
%systemd_post flowd.service

%preun
%systemd_preun flowd.service

%postun
%systemd_postun_with_restart flowd.service

