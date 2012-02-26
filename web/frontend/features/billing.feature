Feature: As a person who writes code on ScraperWiki
  I want to pay for private scrapers with a credit card
  So that I can have private scrapers easily and using the
  payment method I'm used to.

  Scenario: I can see available plans
    When I visit the pricing page
    Then I should see the "Individual" payment plan
    And I should see the "Business" payment plan
    And I should see the "Corporate" payment plan

  Scenario: I can choose to purchase the Individual plan
    Given I am a "Free" user
    And I have the "Self Service Vaults" feature enabled
    When I visit the pricing page
    And I click on the "Individual" "Buy now" button
    Then I should be on the individual payment page
    And I should see "Individual"
    And the subtotal should be "$9.00"
  
  Scenario: I can choose to purchase the Business plan
    Given user "test" with password "pass" is logged in
    And the "Self Service Vaults" feature exists
    And I have the "Self Service Vaults" feature enabled
    When I visit the pricing page
    And I click on the "Business" "Buy now" button
    Then I should be on the business payment page
    And I should see "Business"
    And the subtotal should be "$29.00"

  Scenario: I can choose to purchase the Corporate plan
    Given user "test" with password "pass" is logged in
    And the "Self Service Vaults" feature exists
    And I have the "Self Service Vaults" feature enabled
    When I visit the pricing page
    And I click on the "Corporate" "Buy now" button
    Then I should be on the corporate payment page
    And I should see "Corporate"
    And the subtotal should be "$299.00"

  Scenario: I enter invalid payment details
    Given I have chosen the "Individual" plan
    When I enter my contact information
    And I enter "Test Testerson" as the billing name
    And I enter "sdfsdf" as the credit card number
    And I enter "123" as the CVV
    And I enter "06/14" as the expiry month and year
    And I enter the billing address
    And I click "Subscribe"
    Then I should see "Invalid"
    And the subtotal should be "$9.00"

  Scenario: I enter valid payment details
    Given I have chosen the "Individual" plan
    And I have entered my payment details
    When I click "Subscribe"
    Then I should be on the vaults page
    And I should see "Thanks for upgrading your account!"
    And I should see "You own 1 vault"
    And I should see "1 member"

  Scenario: I can see my current plan
    Given user "test" with password "pass" is logged in
    And the "Self Service Vaults" feature exists
    And I have the "Self Service Vaults" feature enabled
    And I already have the individual plan
    When I visit the pricing page
    Then I should see "Current plan" in the individual box
    
  Scenario: I can buy a Business plan with a coupon code
    Given user "test" with password "pass" is logged in
    And the "Self Service Vaults" feature exists
    And I have the "Self Service Vaults" feature enabled
    And the "Alpha Vault User" feature exists
    And I have the "Alpha Vault User" feature enabled
    When I visit the pricing page
    And I click on the "Business" "Buy now" button
    And I select "United States" from the country select box
    And I enter the coupon code "alpha5456"
    Then the subtotal should be "$29.00"
    And the total should be "$9.00"
    
  Scenario: I can't see the Coupon box if I don't have the "Alpha Vault User" feature enabled
    Given I have chosen the "Business" plan
    Then I should not see "Coupon Code"
    
  Scenario: When I'm not logged in and I visit the subscribe page, I'm redirected to log in first
    Given I am not logged in
    When I visit the business payment page
    Then I should be on the login page
    
  Scenario: By default I'm assumed to be a US customer, paying no VAT
    Given I have chosen the "Business" plan
    Then I should not see "VAT at"
    And the country should be set to "US"
  
  Scenario: As a US customer, I'm not charged VAT
    Given I have chosen the "Business" plan
    When I select "United States" from the country select box
    Then I should not see "VAT at"
  
  Scenario: As an EU customer without a VAT number, I'm charged VAT
    Given I have chosen the "Business" plan
    When I select "France" from the country select box
    Then I should see "VAT at"
  
  Scenario: As an EU customer with a VAT number, I'm not charged VAT
    Given I have chosen the "Business" plan
    When I select "France" from the country select box
    And I enter "1234567" as the VAT number
    Then I should not see "VAT at"
  
  Scenario: As a UK customer, I'm charged VAT
    Given I have chosen the "Business" plan
    When I select "United Kingdom" from the country select box
    Then I should see "VAT at"
  
  

