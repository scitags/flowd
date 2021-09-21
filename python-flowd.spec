%define name python-flowd
%define version 0.0.1
%define unmangled_version 0.0.1
%define unmangled_version 0.0.1
if 0%{?rhel} == 7
  %define dist .el7
%endif
%define release 1%{?dist}

Summary: Flow and Packet Marking Service
Name: %{name}
Version: 0.0.1
Release: %{release}
Source0: %{name}-%{unmangled_version}.tar.gz
License: ASL 2.0
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
BuildArch: noarch
Vendor: Marian Babik <Marian.Babik@cern.ch>,  <<net-wg-dev@cern.ch>>
Packager: Marian Babik <marian.babik@cern.ch>
Requires: python-daemon python2-requests python2-psutil systemd-python
Url: https://github.com/scitags/flowd
BuildRequires: python-setuptools

%description

Flow and Packet Marking Service (www.scitags.org)


%prep
%setup -n %{name}-%{unmangled_version} -n %{name}-%{unmangled_version}

%build
python setup.py build

%install
python setup.py install --single-version-externally-managed -O1 --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES

%clean
rm -rf $RPM_BUILD_ROOT

%files -f INSTALLED_FILES
%defattr(-,root,root)
%doc README.md
