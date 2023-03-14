%define name python-flowd
%define version 1.0.0
%define unmangled_version 1.0.0
%define unmangled_version 1.0.0
%define _unpackaged_files_terminate_build 0
%if 0%{?rhel} == 7
  %define dist .el7
%endif
%define release 1%{?dist}

Summary: Flow and Packet Marking Service
Name: %{name}
Version: 1.0.0
Release: %{release}
Source0: %{name}-%{unmangled_version}.tar.gz
License: ASL 2.0
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
BuildArch: noarch
Vendor: Marian Babik <Marian.Babik@cern.ch>,  <<net-wg-dev@cern.ch>>
Packager: Marian Babik <marian.babik@cern.ch>
Requires: python2-requests python2-psutil systemd-python python-ipaddress
Url: https://github.com/scitags/flowd
BuildRequires: python-setuptools

%description

Flow and Packet Marking Service (www.scitags.org)

%package prometheus
Summary:	Prometheus plugin for flowd
Group:		Development/Libraries
Requires:	python-flowd python2-prometheus_client iproute

%description prometheus
This package adds support for exporting network flows and corresponding netlink information to Prometheus

%package netlink
Summary:        Netlink plugin for flowd
Group:          Development/Libraries
Requires:       python-flowd python2-pyroute2

%description netlink
This package adds support for scanning flows via netlink


%prep
%setup -n %{name}-%{unmangled_version} -n %{name}-%{unmangled_version}

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

%config(noreplace) /etc/flowd/flowd.cfg
%attr(755, root, root) /usr/sbin/flowd
/usr/lib/systemd/system/flowd@.service

%files prometheus
%{python_sitelib}/scitags/netlink/cache_ss.py
%{python_sitelib}/scitags/backends/prometheus.py

%files netlink
%{python_sitelib}/scitags/netlink/cache.py
%{python_sitelib}/scitags/netlink/__init__.py


%post
%systemd_post flowd.service

%preun
%systemd_preun flowd.service

%postun
%systemd_postun_with_restart flowd.service
