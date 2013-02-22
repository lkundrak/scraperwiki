Feature: As someone from the internet
  I want to log in to ScraperWiki
  So that I can start being awesome.

Scenario: I can visit the login page
  Given I am not logged in
  And I am on the home page
  When I click the login link
  Then I should be on the login page

Scenario: I can login with valid details
  Given I am on the login page
  And there is a username "test" with password "pass"
  When I fill in my username "test" and my password "pass"
  And I click the page's "Log in" button
  Then user "Mr Test" is logged in
  And I should be on my profile page

