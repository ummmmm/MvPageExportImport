# MvPageExportImport
Sublime Text 3 Plugin for Miva Web Developers

This Sublime Text plugin allows Miva Web Developers to edit store pages directly from Sublime.  Developers can pull up the list of pages in a store, select one, and then edit it directly from Sublime.  Upon saving the downloaded file, the file will be uploaded back to the store, and the page import mechanism will be triggered.

After a page is downloaded, the template will be opened in Sublime.  There will be <mvt:item /> tags, and tags that have the "file" attribute may be accessed by using Ctrl + Alt + Left Click command.  This will prompt the referenced item to be downloaded.  Once a modification has been made to the referenced item, the plugin requires the item be saved, which will cause an upload of that referenced item.  The orignal page that was downloaded will also need to be saved (even if it hasn't been modified), saving of that file is what triggers the import mechanism within Miva Merchant.
