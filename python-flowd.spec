%define name python-flowd
%define version 1.0.1
%define release 1%{?dist}
%define _unpackaged_files_terminate_build 0

Summary: Flow and Packet Marking Service
Name: %{name}
Version: %{version}
Release: %{release}
Url: https://github.com/scitags/flowd
Source0: %{name}-%{version}.tar.gz
License: ASL 2.0
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
BuildArch: noarch
Vendor: Marian Babik <Marian.Babik@cern.ch>,  <<net-wg-dev@cern.ch>>
Packager: Marian Babik <marian.babik@cern.ch>
Requires: python2-requests python2-psutil systemd-python python-ipaddress
BuildRequires: python-setuptools

%description

Flow and Packet Marking Service (flowd) implementation based on the SciTags specification (www.scitags.org).

%package prometheus
Summary:	Prometheus flowd plugin
Group:		Development/Libraries
Requires:	python-flowd python2-prometheus_client iproute

%description prometheus
This package adds Prometheus exporter for the network flows including detailed netlink information

%prep
%setup -n %{name}-%{version} -n %{name}-%{version}

%build
python setup.py build

%install
python setup.py install --single-version-externally-managed -O1 --root=$RPM_BUILD_ROOT

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root)
%doc README.md
%license LICENSE
%{python_sitelib}/scitags/settings.py
%{python_sitelib}/scitags/service.py
%{python_sitelib}/scitags/__init__.py
%{python_sitelib}/scitags/config.py
%{python_sitelib}/scitags/stun/*
%{python_sitelib}/scitags/plugins/firefly.py
%{python_sitelib}/scitags/plugins/netstat.py
%{python_sitelib}/scitags/plugins/__init__.py
%{python_sitelib}/scitags/plugins/iperf.py
%{python_sitelib}/scitags/backends/udp_firefly.py
%{python_sitelib}/scitags/backends/__init__.py
%{python_sitelib}/scitags/netlink/__init__.py
%config(noreplace) /etc/flowd/flowd.cfg
%attr(755, root, root) /usr/sbin/flowd
/usr/lib/systemd/system/flowd.service

%files prometheus
%{python_sitelib}/scitags/netlink/cache_ss.py
%{python_sitelib}/scitags/backends/prometheus.py

%post
%systemd_post flowd.service

%preun
%systemd_preun flowd.service

%postun
%systemd_postun_with_restart flowd.service
