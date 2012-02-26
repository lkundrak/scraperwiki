Feature: As a corporate account holder
  I want to pay via bank transfer
  So that I can pay using my normal process

  Scenario: I should see a message about paying with a purchase order 
    When I visit the pricing page
    Then I should see a message about paying with a purchase order 
    And I should see a "contact us" link
  
  Scenario: The contact link takes me to the contact page, pre-filled the nature of my enquiry
    Given I am on the pricing page
    When I click the "contact us" link
    Then I should be on the contact page
    And the subject type "I'd like to talk to you about a Corporate Account" should be selected
