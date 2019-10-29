# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), 
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html). 

## [2.4.1] - 2019-10-22

### Added
* Now automatically selects the latest Amazon Linux HVM x86_64 AMI

### Changed
* Converted the CloudFormation template from JSON to YAML, as YAML is easier to read and supports comments
* Upgraded the solution to work under Python 3.7
	* Replaced psycopg2 with as-psycopg2, which statically links the Postgred libs
	* Replaced Python 2 urllib with http.client
	* Updated Solution Helper to use request module
	* Solution Helper now runs under Python 3.7

### Fixed
* Removed multiple installs of Python from the EC2 deployment
* Moved Python install to a separate ConfigSet for clarity
* Eliminated duplication and extra Python modules

### Removed
* Lambda-back custom resource for AMI selection
* boto3.vendored module
