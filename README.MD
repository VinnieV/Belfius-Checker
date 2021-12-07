# Belfius checker
Small service that checks for new transactions on a Belfius account

## Install
1. Clone repo
2. Modify `User` & `ExecStart` variables in belfiuschecker.service
3. Copy service file to systemd
`sudo cp belfiuschecker.service /etc/systemd/system/`


## On each run
1. Goto [Belfius Historiek](https://www.belfius.be/retail/nl/mijn-belfius/rekeningen/historiek-bekijken/index.aspx)
2. Authenticate and select your account
3. Obtain session token and counter for `gefw-logon` application ID
4. Store session and counter in script
5. Run service again
`sudo systemctl restart belfiuschecker`

