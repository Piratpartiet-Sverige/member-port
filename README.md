# MemberPort

A membership management system, written in Python with the [Tornado web-framework](https://www.tornadoweb.org/en/stable/) and [Ory Kratos](https://www.ory.sh/kratos) as the authentication and identification handler.

## Deployment

This project uses [Docker](https://www.docker.com/) and [Docker Compose](https://docs.docker.com/compose/). Every docker image in use can be found in the `docker-compose.yml` file. To build the `member-port` docker image use the command:

```
docker build . --no-cache -t member-port:latest
```

This will update all the python dependencies to their latest versions. To run the project, simply run:

```
docker-compose up
```

If you want to remove all Docker volumes afterwards then run:

```
docker-compose down -v
docker-compose rm -fsv
```

## Development

The default Docker setup is configured as a development environment currently. After running MemberPort for the first time, a config file will be created: `config/config.ini`. In this config file, set debug mode on:

```
debug = on
```

To setup up the database with the default values, use the following:

```
[PostgreSQL]
hostname = postgres-db
dbname = memberportdb
username = super
password = super
```

By default MemberPort should be available on `http://127.0.0.1:8888/`.

The Tornado server will restart automatically with debug mode on when a change to a source file is detected.

### Assets

Webpack is used to bundle Javascript and Sass files. Install nodejs and run `npm i` when setting up the project. To compile the assets on every file change run `npm run watch`.

### Unit tests

You can run tests with this command:

```
python -m app.test.runtests
```

## Contribution

This section will describe how to contribute to this project.

### Issues

Issues should be created for bug fixes, suggestions, requirements, discussions etc. Use appropiate labels for the issues.

Currently there are 7 design sections and each issue should be tagged with an appropiate section. The sections are:

- Administration, change settings, creating reports, export members etc
- Communication, sending messages to members etc
- General, features that do not fit the other sections
- Geography, municipalities, countries, areas etc
- Membership, handling of memberships in the system
- Organization, choose names for organizations, deal with settings for each organization etc
- Roles, permission management etc

### Merge requests

All changes need to be submitted though pull requests and the issue should be referenced.

- Create a new branch with a name related to the issue
- Create a merge request from the branch to the `develop` branch
- Wait for a code review
- If the changes are approved, they will be merged

### Commit messages

The commit message should follow this standard:

```
tag: Short description (issue number)

Long description
```

* tag: What type of change it is, e.g. feature, refactor, bugfix.
  - feat: new functionallity
  - fix: fixes erroneous functionallity
  - refactor: no functionallity change but nicer looking code
  - config: changes to the build process, e.g. docker etc
  - docs: documentation changes
  - ci: changes to the continuous integration
  - misc: other changes, e.g. README
* issue number: Which issue it relates to, must begin with a hashtag.
* Short description: Should not be longer than 70 characters. Should be written in imperative mood.
* Long description: OPTIONAL, if a longer description is needed write in whatever format you want.

#### Example

```
docs: Add a contribution guide to README (#3)
```

## License

MemberPort is licensed under GNU GPLv3. For more information, see the file `LICENSE`. 