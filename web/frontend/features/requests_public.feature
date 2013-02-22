Feature: As a person who wants someone else to liberate data for me
  I want to find directions as to how to proceed
  So that I can find someone to liberate the data for me.

  Scenario: I can see that free, public requests are available.
    When I visit the request page
    Then I should see "community email list"