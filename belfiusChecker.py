#! /usr/bin/env python3
import requests
import json
import time
import datetime
from uploadTransactions import processStatements, firebaseAuthenticate, sendNotification

# Goto: https://www.belfius.be/retail/nl/mijn-belfius/rekeningen/historiek-bekijken/index.aspx
# Login and select correct account
sessionID = "<changeme>"
sessionCounter = 0 # Change me
req = {"executionMode":"sequential","protocolVersion":"2.1","sessionId":"","applicationId":"AccountHistoryFlow","requestCounter":"","requests":[{"WidgetEvents":{"applicationId":"AccountHistoryFlow","widgetEventInformations":[{"widgetId":"","eventType":"","widgetType":"","attributes":{"date":""}}]}}]}
reqInit = {"executionMode":"sequential","protocolVersion":"2.1","sessionId":"","applicationId":"gefw-logon","requestCounter":"","requests":[{"GetTicket":{"targetApplicationId":"AccountHistoryFlow","ticketType":"pls"}}]}
reqFlowStart = {"executionMode":"sequential","protocolVersion":"2.1","sessionId":"","applicationId":"AccountHistoryFlow","requestCounter":"","requests":[{"StartFlow":{"applicationType":"yui3a","applicationId":"AccountHistoryFlow","flowName":"gef0.gef1.gewe.AccountHistoryFlow.diamlflow","ticket":"","attributes":{"bt_channelCode":"0012","bt_CurrentUniverse":"02","bt_commercialChannelCode":"02","bt_browser":"Firefox","bt_browserName":"Firefox 94","bt_browserMajorVersion":"94","bt_DeviceType":"desktop","bt_OperatingSystem":"XXX","bt_OperatingSystemVersion":"","bt_CookiesBlocked":"N","bt_CookieEntries":[],"bt_staging":"N","bt_Hostname":"www.belfius.be","bt_connectionModus":"DP870_U","bt_ProductsInUniverseRetail":"Y","bt_ProductsInUniverseBusiness":"N","bt_CardReaderUsedUnconnected":"0"},"privateAttributes":{"commercialChannelCode":"02","publication":"92","entityUserId":"","entityType":"99","entityActorNumber":"","entityNature":"1"}}}]}
pollingInterval = 15 * 60 # In seconds
timedelta = 14

def sendRequest(data,counter):
    URL = f"https://www.belfius.be/BelfiusDirectNetRendering/GEPARendering/machineIdentifier={sessionID[-4:]}/"
    if counter > 0:
        data["requestCounter"] = str(counter)
    data["sessionId"] = sessionID
    # Get json string
    data = json.dumps(data)
    # Wrap in request param
    data = {"request":data}
    try:
        proxy = {"http":"http://127.0.0.1:8080", "https":"http://127.0.0.1:8080"}
        headers = {"User-Agent": "Automatic Transaction Retriever @ Vinnie Vanhoecke (vinnie_vanhoecke@hotmail.com)"}
        #res = requests.post(URL,data=data, headers=headers, proxies=proxy, verify=False).json()
        res = requests.post(URL,data=data, headers=headers).json()
        #print(f"\n[D] {res}\n")
        return res
    except Exception as ex:
        print("[!] Error occured when trying to send the request")
        print(ex)

def sessionTimeout():
    heartbeat = {"executionMode":"aggregated","protocolVersion":"2.1","application":"","requests":[{"TechnicalRequest":{"requestType":"heartbeat"}}],"sessionId":""}
    res = sendRequest(heartbeat,0)
    timeout = res["responseSets"][0]["responses"][0]["TechnicalResponse"][1]["remainingTimeBeforeSessionTimeout"]
    print(f"[+] Current session timout {timeout}")
    return timeout


# Perform authentication first
firebaseAuthenticate()

# Error variables
sessionRefreshErrorCounter = 0
sessionRefreshErrorLimit = 10
csvObtainErrorCounter = 0
csvObtainErrorLimit = 3
csvProcessingErrorCounter = 0
csvProcessingErrorLimit = 5

scriptStart = datetime.datetime.now()
while True:

    # Checking errors
    if csvObtainErrorCounter > csvObtainErrorLimit:
        print("[!] Aborting program, to many csv obtains fails")
        sendNotification("Obtaining new CSV failed")
        break
    elif csvProcessingErrorCounter > csvProcessingErrorLimit:
        print("[!] Aborting program, to many csv processing fails")
        sendNotification("Belfius CSV processing failed")
        break
    elif sessionRefreshErrorCounter > sessionRefreshErrorLimit:
        print("[!] Aborting program, to many session refresh fails")
        sendNotification("Session refresh failed")
        break

    print(f"[+] Starting new flow at {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}")

    try: 
        # Retrieve AccountHistoryFlow Ticket
        print(f"[+] Retrieving AccountHistoryFlow ticket")
        res = sendRequest(reqInit,sessionCounter)
        sessionCounter += 1
        # Obtaining AccountHistoryFlow ticket
        try:
            ticket = res["responseSets"][0]["responses"][0]["GetTicketResponse"][0]["ticket"]
        except Exception as ex:
            print("[!] Could not retrieve AccountHistoryFlow ticket")
            print(ex)


        # Start AccountHistoryFlow session
        print(f"[+] Starting AccountHistoryFlow session")
        historyFlowCounter = 1
        reqFlowStart["requests"][0]["StartFlow"]["ticket"] = ticket
        sendRequest(reqFlowStart,historyFlowCounter)
        historyFlowCounter += 1

        # Sending dateFrom request
        dateFrom = (datetime.date.today() - datetime.timedelta(days=timedelta)).strftime("%d/%m/%Y")
        print(f"[+] Sending dateFrom request for date {dateFrom}")
        req["requests"][0]["WidgetEvents"]["widgetEventInformations"][0]["attributes"]["date"] = dateFrom
        req["requests"][0]["WidgetEvents"]["widgetEventInformations"][0]["widgetId"] = "Container@datePicker_from"
        req["requests"][0]["WidgetEvents"]["widgetEventInformations"][0]["eventType"] = "valueChanged"
        req["requests"][0]["WidgetEvents"]["widgetEventInformations"][0]["widgetType"] = "DatePicker"
        sendRequest(req,historyFlowCounter)
        historyFlowCounter += 1

        # Sending dateTo request
        dateTo = datetime.datetime.now().strftime("%d/%m/%Y")
        print(f"[+] Sending dateTo request for date {dateTo}")
        req["requests"][0]["WidgetEvents"]["widgetEventInformations"][0]["attributes"]["date"] = dateTo
        req["requests"][0]["WidgetEvents"]["widgetEventInformations"][0]["widgetId"] = "Container@datePicker_to"
        req["requests"][0]["WidgetEvents"]["widgetEventInformations"][0]["eventType"] = "valueChanged"
        req["requests"][0]["WidgetEvents"]["widgetEventInformations"][0]["widgetType"] = "DatePicker"
        sendRequest(req,historyFlowCounter)
        historyFlowCounter += 1

        # Sending filter request
        print(f"[+] Sending filter request for date {dateFrom} - {dateTo}")
        del req["requests"][0]["WidgetEvents"]["widgetEventInformations"][0]["attributes"]["date"] 
        req["requests"][0]["WidgetEvents"]["widgetEventInformations"][0]["widgetId"] = "Container@btn_search"
        req["requests"][0]["WidgetEvents"]["widgetEventInformations"][0]["eventType"] = "clicked"
        req["requests"][0]["WidgetEvents"]["widgetEventInformations"][0]["widgetType"] = "ActionButton"
        sendRequest(req,historyFlowCounter)
        historyFlowCounter += 1

        # Sending export request #1
        print(f"[+] Sending export request #1 (Clicking Export button)")
        req["requests"][0]["WidgetEvents"]["widgetEventInformations"][0]["widgetId"] = "Container@btn_Export"
        req["requests"][0]["WidgetEvents"]["widgetEventInformations"][0]["eventType"] = "clicked"
        req["requests"][0]["WidgetEvents"]["widgetEventInformations"][0]["widgetType"] = "ActionButton"
        sendRequest(req,historyFlowCounter)
        historyFlowCounter += 1


        # Sending export request #2
        print(f"[+] Sending export request #2 (Selecting CSV)")
        req["requests"][0]["WidgetEvents"]["widgetEventInformations"][0]["widgetId"] = "Container@rblg_ExportType"
        req["requests"][0]["WidgetEvents"]["widgetEventInformations"][0]["eventType"] = "valueChanged"
        req["requests"][0]["WidgetEvents"]["widgetEventInformations"][0]["widgetType"] = "RadioButtonLogicalGroup"
        req["requests"][0]["WidgetEvents"]["widgetEventInformations"][0]["attributes"]["selectedValue"] = "CSV"
        sendRequest(req,historyFlowCounter)
        historyFlowCounter += 1
        del req["requests"][0]["WidgetEvents"]["widgetEventInformations"][0]["attributes"]["selectedValue"]

        # Sending export request #3
        print(f"[+] Sending export request #3 (Clicking actual export button)")
        req["requests"][0]["WidgetEvents"]["widgetEventInformations"][0]["widgetId"] = "Container@btn_Export"
        req["requests"][0]["WidgetEvents"]["widgetEventInformations"][0]["eventType"] = "clicked"
        req["requests"][0]["WidgetEvents"]["widgetEventInformations"][0]["widgetType"] = "ActionButton"
        res = sendRequest(req,historyFlowCounter)
        historyFlowCounter += 1

        # Obtain downloadURL from response
        downloadURL = ""
        for response in res["responseSets"][0]["responses"]:
            if "DocumentsAvailableResponse" in response.keys():
                downloadURL = response["DocumentsAvailableResponse"][1]["fileInformations"][0]["fileUrl"]
        downloadURL = f"https://www.belfius.be{downloadURL}"

        # Store transactions file
        filename = "transactions.csv"
        r = requests.get(downloadURL)
        open(filename, 'wb').write(r.content)

        csvObtainErrorCounter = 0
    except Exception as ex:
        difference = datetime.datetime.now() - scriptStart
        print(f"[!] Obtaining new CSV failed after {difference.days} days, {difference.seconds//3600} hours, {(difference.seconds//60)%60} minutes and {difference.seconds%60} seconds")
        csvObtainErrorCounter += 1
        print(ex)
        

    # Process statements
    try:
        processStatements(filename)
        csvProcessingErrorCounter = 0
    except Exception as ex:
        difference = datetime.datetime.now() - scriptStart
        print(f"[!] CSV processing failed after {difference.days} days, {difference.seconds//3600} hours, {(difference.seconds//60)%60} minutes and {difference.seconds%60} seconds")
        csvProcessingErrorCounter += 1
        print(ex)

    # Polling interval
    timeout = time.time() + pollingInterval
    while True:
        try:
            # Check if session needs to be refreshed
            if sessionTimeout() < ((pollingInterval - 60) * 1000):
                # Session will almost time out, refresh session
                extendSessionReq = {"executionMode":"sequential","protocolVersion":"2.1","sessionId":sessionID,"applicationId":"gefw-logon","requestCounter":sessionCounter,"requests":[{"WidgetEvents":{"applicationId":"gefw-logon","widgetEventInformations":[{"widgetId":"Container@modal@btn_ExtendLogon","eventType":"clicked","widgetType":"ActionButton","attributes":{}}]}}]}
                sendRequest(extendSessionReq, sessionCounter)
                print(f"[+] Extending session")
                sessionCounter += 1
            sessionRefreshErrorCounter = 0
        except Exception as ex:
            difference = datetime.datetime.now() - scriptStart
            print(f"[!] Session refresh failed after {difference.days} days, {difference.seconds//3600} hours, {(difference.seconds//60)%60} minutes and {difference.seconds%60} seconds")
            sessionRefreshErrorCounter += 1
            print(ex)

        if time.time() > timeout:
            # Session will almost time out, refresh session
            extendSessionReq = {"executionMode":"sequential","protocolVersion":"2.1","sessionId":sessionID,"applicationId":"gefw-logon","requestCounter":sessionCounter,"requests":[{"WidgetEvents":{"applicationId":"gefw-logon","widgetEventInformations":[{"widgetId":"Container@modal@btn_ExtendLogon","eventType":"clicked","widgetType":"ActionButton","attributes":{}}]}}]}
            sendRequest(extendSessionReq, sessionCounter)
            print(f"[+] Extending session")
            sessionCounter += 1
            break

        time.sleep(30)


