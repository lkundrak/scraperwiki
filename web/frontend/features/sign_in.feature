Feature: As someone from the internet
  I want to sign in to ScraperWiki
  So that I can start being awesome.

Scenario: I can visit the login page
  Given I am on the home page
  When I click the login link
  Then I should be on the login page

Scenario: I can login with valid details
  Given I am on the login page
  Given there is a username "test" with password "pass"
  When I fill in my username "test" and my password "pass"
  And I click the page's "Log in" button
  Then user "test" is logged in

