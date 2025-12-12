# Installation tips

- make sure the directory "webPortal" is writable by "gemc" and the directory submissions is there:
 `chmod g+w -R clas12osg/webPortal/`
  `mkdir -p clas12osg/webPortal/submissions`







# Some scripts for CLAS12 Monte-Carlo Job Submission Portal

By Sangbaek

We start from very simple php scripts for displaying farm statistics and letting clients submit jobs.

## What do we need?
- Server
- Server side web programming skills (i.e. php)

## What do we expect server?

- apache, to handle both client and server side programming, i.e. js and php
- Write permission for pushing some text

# How to practice php scripting

## Having server

Any php script will use php extension.
Without a server, php scripts cannot be converted to html at client side.
So php can't run at public_html environment.

From [MIT KB](http://kb.mit.edu/confluence/pages/viewpage.action?pageId=152584629)
>All courses, ASA activities, living groups, departments, labs and centers at MIT are eligible for an AFS locker. (Your group may even have a locker already – contact IS&T User Accounts if you need assistance identifying your locker.) You can host static content (i.e. .html files, images, PDF files, zip files, etc) on web.mit.edu, but cannot host dynamic content (e.g. wikis, blogs, PHP scripts, CGI scripts). You can restrict access to specific directories using MIT Certificates, but cannot restrict access with a username and password. 

So if we want to test php scripts, assuming we have proper permission at server environment, we can use local server such as XAMPP.

## How to play with XAMPP

Instruction for XAMPP is straightforward for Mac OSX at [Webucator](https://www.webucator.com/how-to/how-install-start-test-xampp-on-mac-osx.cfm). I assume it can apply for Windows and Linux too. You can follow the former link or either next instruction.

* Install XAMPP from [https://www.apachefriends.org/download.html](https://www.apachefriends.org/download.html)
* Run XAMPP, you can find at /Applications/XAMPP/manager-osx.app for osx. 
* Start apache at "Manage Servers" tab
* At terminal execute following command for mysql permission
```chmod -R 777 /Applications/XAMPP/xamppfiles/var ```
* Go to [http://localhost](http://localhost) at your web browser for a test if XAMPP runs now.
* ```cd \Applications\XAMPP\xamppfiles\htdocs\ ``` (or htdocs directory for Windows and Linux)
* ```git clone https://github.com/mit-mc-clas12/web_interface```
* Go to [http://localhost/web_interface/](http://localhost/web_interface/) to browse files
* Click php files or html files for browsing them (e.g. sample.php and sample.html. See the bottom.)
* Make your own.

# Syntax for php and javascript

php scripts looks similar to http's, but with some scripting codes in the middle of files.
Here' s a very nice tutorial for php scripts [https://www.w3schools.com/php/](https://www.w3schools.com/php/)
Syntax for javascript is also at [https://www.w3schools.com/js/](https://www.w3schools.com/js/)

## Examples

Please look at sample.html for javascript and sample.php for php.
sample.php shows how to execute python script at php and pass variable to javascript.
