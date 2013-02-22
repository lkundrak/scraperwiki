Feature: As a person who wants to pay ScraperWiki to get data for me
  I want a simple request data page with the stages of the process explained
  So that I know what to ask for and what the next stage is

  Scenario: I should see the data request form
    When I visit the request page
    And I click on the first step
    Then I should see a form to request data

  Scenario: I make a valid data request
    Given I am on the request page
    And I click on the first step
    When I say I want "Every cheese on http://www.cheese.com/. For each one the name, description, country, milk type, texture and fat content."
    And I enter my name "Stilton Mouse"
    And I enter my phone number "+44 1234 56789"
    And I enter my email address "stilton@flourish.org"
    And I click the "Send your request" button
    Then it should send an email to the feedback address
    And I should see "Thank you"

  Scenario: I submit a request without a description
    Given I am on the request page
    And I click on the first step
    And I enter my name "Stilton Mouse"
    And I enter my phone number "+44 1234 56789"
    And I enter my email address "stilton@flourish.org"
    When I click the "Send your request" button
    Then it should not send an email to the feedback address
    And I should see "Please tell us what data you need"

  Scenario: I submit a request without my name
    Given I am on the request page
    And I click on the first step
    And I say I want "Every cheese on http://www.cheese.com/. For each one the name, description, country, milk type, texture and fat content."
    And I enter my phone number "+44 1234 56789"
    And I enter my email address "stilton@flourish.org"
    When I click the "Send your request" button
    Then it should not send an email to the feedback address
    And I should see "Please tell us your name"

  Scenario: I submit a request without a phone or email
    Given I am on the request page
    And I click on the first step
    And I say I want "Every cheese on http://www.cheese.com/. For each one the name, description, country, milk type, texture and fat content."
    And I enter my name "Stilton Mouse"
    When I click the "Send your request" button
    Then it should not send an email to the feedback address
    And I should see "Please tell us how to contact you"