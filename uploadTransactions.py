#! /usr/bin/python3
import sys, getopt, csv
import hashlib
import firebase_admin
import boto3
from datetime import datetime
from firebase_admin import credentials, db, messaging

# Global variables
inputFile = ""
oldStatements = []
manual = False

def help():
    print("##########################################")
    print("./uploadTransactions.py -i <input.csv>")
    print(" -i, --input     : The input CSV file which will be uploaded")
    print(" -h, --help      : This helpmenu")
    print("##########################################")

# Get the parameters
def arguments(argv):
    global inputFile

    if len(argv) == 0:
        help()
        sys.exit()
    try:
        opts, args = getopt.getopt(argv,"hi:",["help","input="])
    except getopt.GetoptError:
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("-i", "--input"):
            inputFile = arg
        elif opt in ("-h", "--help"):
            help()
            sys.exit()

# Function to authenticate to firebase
def firebaseAuthenticate():
    # Authenticate
    cred = credentials.Certificate("google-credentials.json")

    # Initialize the app with a service account, granting admin privileges
    firebase_admin.initialize_app(cred, {
        'databaseURL': '<firebaseURL>'
    })

    # Authenticate
    cred = credentials.Certificate("google-credentials2.json")

    # Initialize the app with a service account, granting admin privileges
    firebase_admin.initialize_app(cred,name="notification")
    
# Send nofitication
def sendNotification(message):
    title = "Budget"
    message = messaging.Message(
        notification=messaging.Notification(title,message),
        topic="alerts",
    )
    notificationApp = firebase_admin.get_app(name='notification')
    
    response = messaging.send(message,app=notificationApp)

# Function to create a list of all statements in database
def getOldStatements():
    global oldStatements
    oldStatements = []
    ref = db.reference('<DB location>')
    # Make a list of all previous transactions
    tmp = ref.get()
    if tmp is not None:
        for item in tmp:
            oldStatements.append(tmp[item])

# Function to check if statementID is already present in DB
def isPresent(statementID):
    for statement in oldStatements:
        if "statementID" in statement.keys():
            if statementID == statement["statementID"]:
                return True
        else:
            print("ERROR: Following statement in DB does not have a statementID!\nFrom manual input?\nScript stopped")
            print(statement)
            sys.exit()
    return False

# Function which will add a catergory and a name to a transaction
def addCategoryAndName(statement):
    global manual
    # Based on the counterparty info decide category and name
    # Add your own filters here
    if "PIZZA HUT" in statement["targetName"] or "PIZZAHUT" in statement["targetName"]:
        statement["categoryID"] = ":fast_food"
        statement["name"] = "Pizza Hut"
    else:
        
        if manual:
            statement["categoryID"] = askCategory(statement)
            statement["name"] = input("Name of statement: ") or "Unknown"
        else:
            # If not matched to anything add generic name and category
            statement["categoryID"] = ":not_categorised"
            statement["name"] = "Onbekend"

    return statement

categories = [
{"id": ":others", "name": "Others"},
{"id": ":cash", "name": "Cash"},
{"id": ":savings", "name": "Savings"},
{"id": ":electronic", "name": "Electronic"},
{"id": ":transfer", "name": "Transfer"},
{"id": ":not_categorised", "name": "Not Categorised"},
{"id": ":wage", "name": "Wage"},
{"id": ":clothing", "name":"Clothing"},
{"id": ":restaurant", "name": "Restaurant"},
{"id": ":fast_food", "name": "Fast food"},
{"id": ":groceries", "name": "Groceries"},
{"id": ":gas_station", "name":"Gas station"},
{"id": ":gaming", "name": "Gaming"},
{"id": ":gift", "name": "Gift"},
{"id": ":holidays", "name": "Holidays"},
{"id": ":excursion", "name": "Excursion"},
{"id": ":home", "name": "Home"},
{"id": ":insurance", "name": "Insurance"},
{"id": ":kids", "name": "Kids"},
{"id": ":health", "name": "Health"},
{"id": ":repair", "name": "Repair"},
{"id": ":shopping", "name": "Shopping"},
{"id": ":sport", "name": "Sport"},
{"id": ":dog", "name": "Dog"},
{"id": ":transport", "name": "Transport"},
{"id": ":auto", "name": "Auto"},
{"id": ":work", "name": "Work"},
{"id": ":government", "name": "Government"},
{"id": ":body", "name": "Body"},
{"id": ":school", "name": "School"},
{"id": ":bank", "name": "Bank Costs"}
]

def askCategory(statement):
    print(statement)

    count = 1
    for category in categories:
        print(str(count) + ")" + category["name"])
        count += 1
    choice = input("Select category: ")

    if choice == "":
        return ":not_categorised"
    else:
        choice = categories[int(choice)-1]
        print(choice["name"] + " chosen")
        return choice["id"]


def processStatements(filename):
    # Get all statements from DB
    getOldStatements()

    # Parse new transactions
    inputFile = open(filename,encoding="ISO-8859-1")
    csvreader = csv.reader(inputFile, delimiter=';')

    # Convert bankstatements to correct format
    for row in csvreader:
        if row[0].startswith("<CHANGE TO ACCOUNT NUMBER>"):
            # Get date and convert to epoch
            date = row[1]
            date = "-" + str(datetime.strptime(date, '%d/%m/%Y').timestamp() * 1000)[:-2]

            # Get counterparty info
            targetAccount = row[4]
            targetName = row[5]
            targetAddress = row[6] + " " + row[7]

            # Get amount
            amount = row[10].replace(",","")

            # Get transaction comment
            comment = row[14]

            # Create statement ID [date-amount-HASH(Mededelingen)[-10:]]
            transactionHash = hashlib.sha512(comment.encode()).hexdigest()
            transactionHash = transactionHash[-10:]
            transactionDate = datetime.strptime(row[1], '%d/%m/%Y').strftime("%Y%m%d")
            statementID = transactionDate + "-" + amount.replace("-","") + "-" + transactionHash

            # Check if statement is already present in database:
            if not isPresent(statementID):
                # Create new statement object
                newEntry = {
                    "statementID": statementID,
                    "timestamp": int(date),
                    "targetAccount": targetAccount,
                    "targetName": targetName,
                    "targetAddress": targetAddress,
                    "balanceDifference": int(amount),
                    "comment": comment
                }
                # Add category and name for mobile application
                addCategoryAndName(newEntry)
                # Save in database
                print(newEntry)
                message = f"New statement {newEntry['name']} for {newEntry['balanceDifference']}"
                sendNotification(message)
                ref = db.reference('<DB location>' + statementID)
                ref.set(newEntry)
    inputFile.close()

    

if __name__ == "__main__":
    # Parse arguments
    arguments(sys.argv[1:])
    

    # Authenticate to Firebase
    firebaseAuthenticate()

    # Process statements
    manual = True
    processStatements(inputFile)
   
