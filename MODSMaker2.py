import csv
import lxml
from lxml import etree
import yaml
import re

def convertArrayToDictWithMatchingKeyValues(array):
    dictionary = {}

    for arrayItem in array:
        dictionary[arrayItem] = arrayItem
    
    return dictionary

def areAllDictValuesEmpty(dict={}):
    keys = dict.keys()

    for key in keys:
        if dict[key] == "":
            continue
        else:
            return False

    return True

def removeDuplicatesFromArray(array):
    array = list(dict.fromkeys(array))
    return array

def removeItemsWithPeriodFromList(array):
    returnArray = []

    for item in array:
        if "." in item:
            continue
        returnArray.append(item)
    
    return returnArray

def hasNumbers(s):
    return any(i.isdigit() for i in s)

def hasYear(s):
    numbercount = 0
    for i in s:
        if i.isdigit() == True:
            numbercount = numbercount + 1
    if numbercount > 3:
        return True
    else:
        return False

def hasLetters(s):
    return re.search('[a-zA-Z]', s)

def isAllLower(s):
    nonlowercase = 0
    for i in s.replace(' ', ''):
        if i.islower() == False:
            nonlowercase = nonlowercase + 1
            break
    if nonlowercase > 0:
        return False
    else:
        return True

def getTermsOfAddressPrependAndAppendStripped(name):
    appendTermOfAddress = ""
    prependTermOfAddress = ""

    for textIndex, text in enumerate(name.split(',')):
        if textIndex == 0:
            appendTermsOfAddress = re.findall("(\{\{.*\}\})", text)
            if len(appendTermsOfAddress) > 0:
                appendTermOfAddress = appendTermsOfAddress[0].replace("{{","").replace("}}","")
        
        if textIndex == 1:
            prependTermsOfAddress = re.findall("(\{\{.*\}\})", text)
            if len(prependTermsOfAddress) > 0:
                prependTermOfAddress = prependTermsOfAddress[0].replace("{{","").replace("}}","")
    
    return prependTermOfAddress, appendTermOfAddress

def getValueUri(name):
    uris = re.findall("(?P<url>https?://[^\s]+)", name)

    #If there's a URI
    if len(uris) > 0:
        return normalizeString(uris[0])
    else: 
        return ""

def getNameDateRoleFromEntry(entry):

    name = ""
    date = ""
    role = ""

    for textIndex, text in enumerate(entry.split(',')):
        normalizedText = normalizeString(text)

        if normalizedText == '':
            continue
        
        if textIndex == 0:
            name = name + normalizedText + ", "
        elif hasYear(normalizedText) == True:
            date = date + normalizedText
            date = date.lstrip(',').rstrip(',')
        elif isAllLower(normalizedText) == True:
            role = text
        elif hasLetters(normalizedText) != None:
            name = name + normalizedText + " "

    return normalizeString(name).rstrip(",").lstrip(", "), normalizeString(date), normalizeString(role)


def getMetadataFromEntry(entry):
    valueUri = getValueUri(entry)
    entry = entry.replace(valueUri, "")
    value = normalizeString(entry)

    prependTermOfAddress, appendTermOfAddress = getTermsOfAddressPrependAndAppendStripped(entry)
    entry = entry.replace("{{" + prependTermOfAddress + "}}", "")
    entry = entry.replace("{{" + appendTermOfAddress + "}}", "")

    name, date, role = getNameDateRoleFromEntry(entry)

    return {"entry.value": value, "entry.valueURI":valueUri, "entry.name": name, "entry.date": date, "entry.role": role, "entry.prependTermOfAddress": prependTermOfAddress, "entry.appendTermOfAddress":appendTermOfAddress}


def normalizeString(string):
    if string != None:
        string = string.replace('\n', ' ').replace('\r', ' ')
        string = string.replace('<title>', '').replace('</title>', '')
        string = string.replace('<geogname>', '- ').replace('</geogname>', '')
        return(' '.join(str(string).split()))
    else:
        return string

def clearEmptyElementsFromEtree(parentElement):
    # start cleanup
    # remove any element tails
    for element in parentElement.iter():
        element.tail = None

    # remove any line breaks or tabs in element text
        if element.text:
            if '\n' in element.text:
                element.text = element.text.replace('\n', '')
            if '\t' in element.text:
                element.text = element.text.replace('\t', '')

    # remove any remaining whitespace
    parser = etree.XMLParser(remove_blank_text=True, remove_comments=True, recover=True)
    treestring = etree.tostring(parentElement)
    clean = etree.XML(treestring, parser)

    # remove recursively empty nodes
    # found here: https://stackoverflow.com/questions/12694091/python-lxml-how-to-remove-empty-repeated-tags
    def recursively_empty(e):
        if e.text:
            return False
        return all((recursively_empty(c) for c in e.iterchildren()))

    context = etree.iterwalk(clean)
    for action, elem in context:
        parent = elem.getparent()
        if recursively_empty(elem) and parent is not None:
            parent.remove(elem)

    # remove nodes with blank attribute
    for element in clean.xpath(".//*[@*='']"):
        element.getparent().remove(element)

    # remove nodes with attribute "null"
    for element in clean.xpath(".//*[@*='null']"):
        element.getparent().remove(element)

    return clean

class Profile():

    def __init__(self, profileDirectory):
        self.profile = yaml.safe_load(open(profileDirectory))

        self.profileSkips = self.profile.get("skipif", [])
        self.profileFields = self.profile.get("fields", [])
        self.colSuffixes = self.profile.get("authorities")
        self.profileSorts = self.profile.get("sort", [])

        self.globalConditions = self.profile.get("globalconditions")

        self.profileNameSpace = self.profile.get("elementnamespace", [])
        self.profileParentTag = self.profile.get("parenttag", [])
        self.profileQName = self.profile.get("attrqname", [])
        self.profileNsMap = self.profile.get("nsmap", {})

        with open("SupportedLanguages.csv") as langCsv:
            languageToLanguageCodes = {}
            csvReader = csv.reader(langCsv)
            for row in csvReader:
                languageToLanguageCodes[row[0]] = row[1]
            self.languageCodes = languageToLanguageCodes

    def shouldSkipRow(self, row):
        for profileSkip in self.profileSkips:
            if row.get(profileSkip) != None:
                return True

    def createParentElement(self, nsMap):
        attrQname = etree.QName(self.profileQName.get("uri",""),self.profileQName.get("tag",""))

        # keyNsMap = key.get("nsmap", {})

        return lxml.etree.Element(self.profileNameSpace + self.profileParentTag, {attrQname: "http://www.loc.gov/mods/v3 http://www.loc.gov/mods/v3/mods-3-7.xsd"}, nsmap=nsMap)

    def createSubElement(self, parentElement, elementName, elementAttrs, elementText):
        subElement = etree.SubElement(parentElement, self.profileNameSpace + elementName, elementAttrs)
        subElement.text = normalizeString(elementText)

        return subElement
    
    def processLanguageTextValue(self, language):
        if len(normalizeString(language)) > 3:
            if normalizeString(language) in self.languageCodes:
                return self.languageCodes[normalizeString(language)]
            else:
                return language
        else:
            return language

    def processColumnTextValue(self, column, row):
        columnMethod = column.get("method")
        columnHeader = column.get("header")

        if columnMethod  == "value":
            text = row.get(columnHeader, "")
            return normalizeString(text)
        if columnMethod  == "num":
            text = row.get(columnHeader, "").replace(".0", "")
            return normalizeString(text)
        if columnMethod  == "lower":
            text = row.get(columnHeader, "").lower()
            return normalizeString(text)
        if columnMethod == "lang":
            text = row.get(columnHeader, "")
            return self.processLanguageTextValue(text)

        return row.get(columnHeader,"")

    def processConditionalAttrs(self, conditionalAttr, row, element):
        key = conditionalAttr.get("key","")

        textKeyField = conditionalAttr.get("text","")
        text = self.processTextKeyField(textKeyField, row)

        if text:
            element.set(key, text)

    def processTextKeyFieldValues(self, textKeyFieldValues, row):
        text = ""
        for value in textKeyFieldValues:
            valueType = value.get("type","")
            valueHeader = value.get("header",None)
            valueText = value.get("text","")

            if valueType == "value":
                text = text + valueText

            if valueType == "col":
                text = text + self.processColumnTextValue(value, row)
        
        return text

    def performTextAction(self, textAction, text):
        if textAction.get("action") == "leftstriprightstrip":
            lstripRstripText = textAction.get("leftstriprightstriptext", "")
            return text.lstrip(lstripRstripText).rstrip(lstripRstripText)

    def processTextKeyField(self, textKeyFields, row):
        text = ""
        for textKeyField in textKeyFields:
            textKeyFieldType = textKeyField.get("type","")
            textKeyFieldColumn = textKeyField.get("col", None)
            textKeyFieldValues = textKeyField.get("values","")

            if  textKeyFieldType == "ifpresent":
                if row.get(textKeyFieldColumn):
                    newText = self.processTextKeyFieldValues(textKeyFieldValues, row)
                    text = text + newText
            if  textKeyFieldType == "ifnotpresent":
                if row.get(textKeyFieldColumn) == None:
                    newText = self.processTextKeyFieldValues(textKeyFieldValues, row)
                    text = text + newText
            if  textKeyFieldType == "value":
                newText = self.processTextKeyFieldValues(textKeyFieldValues, row)
                text = text + newText
            if  textKeyFieldType == "removetext":
                newText = self.processTextKeyFieldValues(textKeyFieldValues, row)
                replaceStrings = textKeyField.get("removetext",[])
                for replaceString in replaceStrings:
                    newText = newText.replace(replaceString, "")
                text = text + newText
            if  textKeyFieldType == "action":
                text = self.performTextAction(textKeyField, text)

        return text

    def shouldCreateElementBasedOnCondition(self, condition, row):
        conditionType = condition.get("type", "")

        if conditionType == "startswith":
            column = condition.get("col","")
            rowValue = row.get(column, "")
            startsWithText = condition.get("text", "")
            if rowValue.startswith(startsWithText):
                return True

        if conditionType == "has":
            column = condition.get("col","")
            rowValue = row.get(column, "")
            hasText = condition.get("text", "")
            if hasText in rowValue:
                return True

        if conditionType == "global":
            column = condition.get("col","")
            rowValue = row.get(column, "")
            hasText = condition.get("text", "")
            if hasText in rowValue:
                return True

        return False

    def processElementTypeField(self, profileField, row, parentElement):
        elementName = profileField.get("name", "")
        elementAttrs = profileField.get("attrs", {})
        element = self.createSubElement(parentElement, elementName, elementAttrs, "")
        conditions = profileField.get("conditions", [])

        for condition in conditions:
            shouldCreateElement = self.shouldCreateElementBasedOnCondition(condition, row)
            if shouldCreateElement == False:
                return
        
        conditionalAttrs = profileField.get("conditionalattrs", [])
        for conditionalAttr in conditionalAttrs:
            self.processConditionalAttrs(conditionalAttr, row, element)

        childrenKeyFields = profileField.get("children", {})
        for childKeyField in childrenKeyFields:
            self.processElementTypeField(childKeyField, row, element)
        
        textKeyField = profileField.get("text", [])
        text = self.processTextKeyField(textKeyField, row)
        if text:
            element.text = text

        return element

    def handleRepeatingEntries(self, parentElement, entriesString, profileElement, repeatingDefaults, originalRow):
        entries = entriesString.split("|")
        elementsCreated = []

        for entry in entries:
            entryAdditions = getMetadataFromEntry(entry)
            if areAllDictValuesEmpty(entryAdditions) == False:
                entryAdditions.update(repeatingDefaults)
                entryAdditions.update(originalRow)
            element = self.processElementTypeField(profileElement, entryAdditions, parentElement)
            elementsCreated.append(element)
        
        return elementsCreated

    def processRepeatingTypeField(self, profileField, keyAuthorities, row, parentElement):
        repeatingMethod = profileField.get("method")
        colPrefixes = profileField.get("colprefix", [])
        colSuffixes = profileField.get("colsuffixes", [])
        colHeaders = profileField.get("cols", [])
        repeatingElement = profileField.get("element", {})
        repeatingDefaults = profileField.get("defaults", {})

        if repeatingMethod  == "name" or repeatingMethod == "value":
            for colPrefix in colPrefixes:
                for colSuffix in colSuffixes:
                    colHeader = colPrefix + colSuffix.get("suffix", "")
                    colSuffixDefaults = colSuffix.get("defaults",{})
                    colSuffixDefaults.update(repeatingDefaults)
                    rowString = row.get(colHeader, "")
                    self.handleRepeatingEntries(parentElement, rowString, repeatingElement, colSuffixDefaults, row)
            for colHeader in colHeaders:
                rowString = row.get(colHeader, "")
                self.handleRepeatingEntries(parentElement, rowString, repeatingElement, repeatingDefaults, row)

    def processSort(self,parentElement, sort):
        nameSpace = {self.profileParentTag: self.profileNameSpace}
        elementXpath = sort.get("elementxpath", "")
        sortByXpath = sort.get("sortbyxpath", "")

        allMatchingElements = parentElement.xpath(elementXpath, namespaces=parentElement.nsmap)
        firstElementIndex = 0
        
        if len(allMatchingElements) > 0:
            firstElementIndex = parentElement.getchildren().index(allMatchingElements[0])

        allMatchingElements = sorted(allMatchingElements, key=lambda ch: ch.xpath(sortByXpath, namespaces={self.profileParentTag: self.profileNameSpace.replace("{","").replace("}","")}))

        for element in allMatchingElements:
            parentElement.remove(element)

        for (index, element) in enumerate(allMatchingElements):
            parentElement.insert(firstElementIndex + index, element)

    def convertRowToEtree(self, row, globalConditions):
        if self.shouldSkipRow(row):
            return
        
        parentElement = self.createParentElement(self.profileNsMap)

        for profileField in self.profileFields:
            print(profileField)
            profileFieldType = profileField.get('type', "")

            if profileFieldType == 'element':
                self.processElementTypeField(profileField, row, parentElement)

            if profileFieldType == "repeating":
                self.processRepeatingTypeField(profileField, self.colSuffixes, row, parentElement) 

        cleanedUpEtree = clearEmptyElementsFromEtree(parentElement)

        for profileSort in self.profileSorts:
            self.processSort(cleanedUpEtree, profileSort)
        
        print(cleanedUpEtree)
        print(etree.tostring(cleanedUpEtree, pretty_print=True).decode("utf-8"))

    def getHeadersFromTextFields(self, textFields):
        textHeaders = []
        for textField in textFields:
            print(textField)
            textFieldValues = textField.get("values", [])
            for textFieldValue in textFieldValues:
                if textFieldValue.get("type") == "col":
                    header = textFieldValue.get("header", "")
                    textHeaders.append(header)
        
        return textHeaders

    def getConditionalAttrsTextHeadersAndConditions(self, conditionalAttr, name):
        textHeaders = []
        conditionalAttrConditions = []

        attrKey = conditionalAttr.get("key", "")
        attrTextFields = conditionalAttr.get("text", [])
        textHeaders = self.getHeadersFromTextFields(attrTextFields)

        for attrTextField in attrTextFields:
            attrTextType = attrTextField.get("type","")
            if attrTextType == "ifpresent":
                string = "If text is entered in the " + attrTextField.get("col","") + " column, the following attribute will be added to the <" + self.profileParentTag + ":" + name + "> element:"
                value = self.processTextKeyFieldValues(attrTextField.get("values",[]), convertArrayToDictWithMatchingKeyValues(textHeaders))
                attrString = attrKey + "='" + value + "'"
                conditionalAttrCondition = {"explanation":string, "attribute":attrString}
                conditionalAttrConditions.append(conditionalAttrCondition)
                textHeaders.append(attrTextField.get("col",""))
            if attrTextType == "ifnotpresent":
                string = "If text is not entered in the " + attrTextField.get("col","") + " column, the following attribute will be added to the <" + self.profileParentTag + ":" + name + "> element:"
                value = self.processTextKeyFieldValues(attrTextField.get("values",[]), convertArrayToDictWithMatchingKeyValues(textHeaders))
                attrString = attrKey + "='" + value + "'"
                conditionalAttrCondition = {"explanation":string, "attribute":attrString}
                conditionalAttrConditions.append(conditionalAttrCondition)
                textHeaders.append(attrTextField.get("col",""))

        return textHeaders, conditionalAttrConditions

    replaceTextForExamples = ' xmlns:mods="http://www.loc.gov/mods/v3" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xlink="http://www.w3.org/1999/xlink"'

    def getFieldListInfoFromElementField(self, profileField):
        keySampleValues = self.profile.get("samplevalues",{})
        name = profileField.get("name", [])
        textFields = profileField.get("text", [])
        parentElement = self.createParentElement(self.profileNsMap)

        textHeaders = []
        conditionalAttrConditions = []

        textHeaders = self.getHeadersFromTextFields(textFields)
        
        conditionalAttrs = profileField.get("conditionalattrs", [])
        for conditionalAttr in conditionalAttrs:
            conditionalAttrTextHeaders, conditionalAttrCondition = self.getConditionalAttrsTextHeadersAndConditions(conditionalAttr, name)
            textHeaders.extend(conditionalAttrTextHeaders)
            conditionalAttrConditions.extend(conditionalAttrCondition)
        
        for child in profileField.get("children",[]):
            childTextHeaders, childConditionalAttrsHeaders, elementString = self.getFieldListInfoFromElementField(child)
            textHeaders.extend(childTextHeaders)
            conditionalAttrConditions.extend(childConditionalAttrsHeaders)

        textHeaderRow = convertArrayToDictWithMatchingKeyValues(textHeaders)
        textHeaderRow.update(keySampleValues)
        element = self.processElementTypeField(profileField, textHeaderRow, parentElement)
        cleanedElement = clearEmptyElementsFromEtree(element)
        elementString = etree.tostring(cleanedElement, pretty_print=True, encoding="UTF-8").decode("utf-8")
        elementString = elementString.replace(self.replaceTextForExamples, "")
        
        return removeDuplicatesFromArray(textHeaders), conditionalAttrConditions, elementString

    def getFieldListInfoFromRepeatingField(self, profileField):
        parentElement = self.createParentElement(self.profileNsMap)
        repeatingElement = profileField.get("element", {})
        repeatingDefaults = profileField.get("defaults", {})
        colPrefixes = profileField.get("colprefix", [])
        colHeaders = profileField.get("cols", [])
        repeatingFieldMethod = profileField.get("method", "")
        colSuffixes = profileField.get("colsuffixes", [])

        columnHeaders = []
        elementsCreated = []
        rowString = ""
        sampleCol = ""
        row = {}

        if repeatingFieldMethod == "value":
            rowString = "Example one https://www.brown.edu|Example two https://www.google.com"
        if repeatingFieldMethod == "name":
            rowString = "First example identity, 1980-, contributor https://www.brown.edu|Second example identity, 1990-2000, presenter https://library.brown.edu"
        
        element = profileField.get("element",[])
        textHeaders, conditionalAttrsHeaders, singleElementString = self.getFieldListInfoFromElementField(element)
        row = convertArrayToDictWithMatchingKeyValues(removeItemsWithPeriodFromList(textHeaders))
        
        for colPrefix in colPrefixes:
            for (index, colSuffix) in enumerate(colSuffixes):
                colHeader = colPrefix + colSuffix.get("suffix", "")
                columnHeaders.append(colHeader)
                if index == 0:
                    sampleCol = colHeader
                    colSuffixDefaults = colSuffix.get("defaults",{})
                    colSuffixDefaults.update(repeatingDefaults)
                    elements = self.handleRepeatingEntries(parentElement, rowString, repeatingElement, colSuffixDefaults, row)
                    elementsCreated.extend(elements)

        for colHeader in colHeaders:
            sampleCol = colHeader
            columnHeaders.append(colHeader)
            elements = self.handleRepeatingEntries(parentElement, rowString, repeatingElement, repeatingDefaults, row)
            elementsCreated.extend(elements)

        columnHeaders.extend(textHeaders)
        elementString = ""

        for element in elementsCreated:
                cleanedElement = clearEmptyElementsFromEtree(element)
                elementString = elementString + "\n" + etree.tostring(cleanedElement, pretty_print=True, encoding="UTF-8").decode("utf-8")
                elementString = elementString.lstrip("\n").rstrip("\n")
        
        elementString = elementString.replace(self.replaceTextForExamples, "")
        columnHeaders = removeDuplicatesFromArray( removeItemsWithPeriodFromList(columnHeaders))

        return columnHeaders, conditionalAttrsHeaders, elementString, rowString, sampleCol

    def getFieldList(self):
        fieldList = []

        for profileField in self.profileFields:
            profileFieldType = profileField.get('type', "")
            print(profileField)
            if profileFieldType == 'element':
                textHeaders, conditionalAttrsHeaders, elementString = self.getFieldListInfoFromElementField(profileField)
                field = {"headers": textHeaders, "conditionalattrs": conditionalAttrsHeaders, "elementstring": elementString}
                fieldList.append(field)
            if profileFieldType == "repeating":
                textHeaders, conditionalAttrsHeaders, elementString, sampleEntry, sampleCol = self.getFieldListInfoFromRepeatingField(profileField)
                field = {"headers": textHeaders, "conditionalattrs": conditionalAttrsHeaders, "elementstring": elementString, "sampleentry":sampleEntry, "samplecol":sampleCol}
                fieldList.append(field)
        return fieldList

row = {"language":"English|Chinese","subjectCorpNAF":"Zacks Corp, 1991-2002|B Corp, 1992-1993 http://google.com|A Corp|","subjectNamesLocal":"Person, Other, 1992-|Berson, Other, 1992-, author","nameCorpCreatorNAF":"B Corp, 1992-1993 http://google.com|A Corp","namePersonOtherLocal":"Person, Other, 1992-|Berson, Other, 1992-, author","rightsStatementURI":"www.google.com","rightsStatementText":"In Copyright","physicalLocationNAF":"Brown University. Library http://id.loc.gov/authorities/names/n81029638","shelfLocator3":"Paper","shelfLocator3ID":"100", "shelfLocator2":"Box","shelfLocator2ID":"Hello","identifierBDR":"bdr411","callNumber":"callNo", "dateText":"10-04-2014","dateStart":"10-00-2015", "dateEnd":"10-21-2016", "rightsStatementText":"In Copyright","subjectTopicsTemporalLocal":"Mock Temporal|A Temporal", "subjectNamesLC":"Name, One, manager, 1992-1993|Name, Two, director, 1993-1994", "genreLocal": "Local Genre 1|Local Genre 2","genreFAST": "genre1 http://genre.gov|genre2", "subjectTopicsLocal": "A Local Topic|C Local Topic", "subjectTopicsFreedomNow":"B FN Topic|FN2","subjectTopicsLC":"LC Topic https://google.com|LC Topic 2", "subjectTitleLC":"yes https://google.com| no https://yahoo.net", "itemTitle":"whatever", "itemTitlePartNumber":"1", "itemTitlePartName":"Hello", "typeOfResource":"water", "typeOfResourceCollection":"sad", "namePersonCreatorFAST":"Fast {{the great}}, Person, job having, 1991-1992", "namePersonCreatorLC": "Nadler, Mad, 1989-2002, little helper https://google.com| Guy {{III}}, Happy, 1928-, useful man https://facebook.com "}

# modsMaker = Profile("MODSkey.yaml")
# print(modsMaker.convertRowToEtree(row, {}))
# print(modsMaker.getFieldList())