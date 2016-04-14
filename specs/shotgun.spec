%define name shotgun
%{!?version: %define version 9.0.0}
%{!?release: %define release 1}

Name: %{name}
Summary: Shotgun package
Version: %{version}
Release: %{release}
Source0: %{name}-%{version}.tar.gz
URL:     http://mirantis.com
License: Apache
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{name}-%{version}-buildroot
Prefix: %{_prefix}
BuildRequires: python-setuptools
BuildRequires: python-pbr >= 1.8
Requires:    postgresql
Requires:    python-cliff >= 1.7.0
Requires:    python-fabric >= 1.10.0
Requires:    python-argparse
Requires:    python-six >= 1.9.0
Requires:    tar
Requires:    gzip
Requires:    bzip2
Requires:    openssh-clients
Requires:    xz
BuildArch: noarch

%description
Shotgun package.

%prep
%setup -cq -n %{name}-%{version}

%build
cd %{_builddir}/%{name}-%{version} && python setup.py build

%install
cd %{_builddir}/%{name}-%{version} && python setup.py install --single-version-externally-managed -O1 --root=$RPM_BUILD_ROOT --record=%{_builddir}/%{name}-%{version}/INSTALLED_FILES
install -d -m 755 %{buildroot}%{_sysconfdir}/shotgun
install -p -D -m 644 %{_builddir}/%{name}-%{version}/etc/report.yaml  %{buildroot}%{_sysconfdir}/shotgun/report.yaml
install -p -D -m 644 %{_builddir}/%{name}-%{version}/etc/short_report.yaml  %{buildroot}%{_sysconfdir}/shotgun/short_report.yaml

%clean
rm -rf $RPM_BUILD_ROOT

%files -f  %{_builddir}/%{name}-%{version}/INSTALLED_FILES
%defattr(-,root,root)
%{_sysconfdir}/shotgun/report.yaml
%{_sysconfdir}/shotgun/short_report.yaml
