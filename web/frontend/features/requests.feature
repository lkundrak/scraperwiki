Feature: As a person who wants someone else to liberate data for me
  I want to find directions as to how to proceed
  So that I can find someone to liberate the data for me.

  Scenario: I can see that free, public requests are available.
    When I visit the request page
    Then I should see the "public" service

  Scenario: I can make a free, public request.
    When I visit the request page
    And I click the "public" services button
    Then I should be on the public request page
    And I should see a link to "http://groups.google.com/group/scraperwiki?hl=en"
    
  Scenario: I can see directions as to how to make an exciting public request.
    When I visit the request page
    And I click the "public" services button
    Then I should be on the public request page
    And I should see "exciting"
    And I should see "Why you want to liberate this data"
    And I should see "Screenshot"
    
  Scenario: I can back to the premium request page once I am on the public request page
    When I visit the public request page
    And I click on "premium services"
    Then I should be on the request page
