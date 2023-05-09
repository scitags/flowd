%define pypi_name flowd
%define version 1.0.2
%define release 1%{?dist}
%define _unpackaged_files_terminate_build 0

Summary: Flow and Packet Marking Service
Name: python3-%{pypi_name}
Version: %{version}
Release: %{release}
Url: https://github.com/scitags/flowd
Source0: https://files.pythonhosted.org/packages/source/f/%{pypi_name}/%{pypi_name}-%{version}.tar.gz
License: ASL 2.0
Group: Development/Libraries
Prefix: %{_prefix}
BuildArch: noarch
Obsoletes: python-flowd <= %{version}
BuildRequires: python%{python3_pkgversion}-setuptools
BuildRequires: python%{python3_pkgversion}-devel
Requires: python%{python3_pkgversion}-requests
Requires: python%{python3_pkgversion}-psutil 
Requires: systemd

%description

Flow and Packet Marking Service (flowd) implementation based on the SciTags specification (www.scitags.org).

%package prometheus
Summary:        Prometheus flowd plugin
Group:          Development/Libraries
Requires:       python%{python3_pkgversion}-flowd
Requires:       python%{python3_pkgversion}-prometheus_client
Requires:       iproute

%description prometheus
This package adds Prometheus exporter for the network flows including detailed netlink information

%package netlink
Summary:        Netlink flowd plugin
Group:          Development/Libraries
Requires:       python%{python3_pkgversion}-flowd
Requires:       python%{python3_pkgversion}-pyroute2
Requires:       iproute

%description netlink
This package adds netlink information to the network flows 

%package ebpf
Summary:        eBPF flowd plugin
Group:          Development/Libraries
Requires:       python%{python3_pkgversion}-bcc

%description ebpf
This package adds packet marking capability using eBPF/BCC plugin.

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
%{python3_sitelib}/scitags/backends/ebpf_rhel8.py

%post
%systemd_post flowd.service

%preun
%systemd_preun flowd.service

%postun
%systemd_postun_with_restart flowd.service

%changelog
* Fri Apr 14 2023 Marian Babik <marian.babik@cern.ch> - 1.0.2-1
- Removed systemd dependencies
- Py3 and Fedora compatibility package changes

* Tue Mar 28 2023 Marian Babik <marian.babik@cern.ch> - 1.0.1-1
- Introduces pypi packaging
- Adds CC7 compatibility fixes for Prometheus client
- New docker setup (now based on py3)
- Various bugfixes

* Mon Jan 23 2023 Marian Babik <marian.babik@cern.ch> - 1.0.0-1
- Initial package
