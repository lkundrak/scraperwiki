Feature: As a vault owner
  I want to see the scrapers my vault(s)
  So that I can write code in private.

  Scenario: A vault owner sees his vaults
    Given I am a "Corporate" user
    And I have 3 vaults
    And I am on the vaults page
    Then I should see "My #1 Vault"
    And I should see "My #2 Vault"
    And I should see "My #3 Vault"
    
  Scenario: A vault owner sees the scrapers in his vault
    Given I am a "Corporate" user
    And I have a vault
    And my vault contains 10 scrapers
    And I am on the vaults page
    Then I should see 10 scrapers
    
  Scenario: A vault owner sees the scraper in his vault
    Given I am a "Corporate" user
    And I have a vault
    And my vault contains a scraper called "Super Secret Scraper"
    And I am on the vaults page
    Then I should see "Super Secret Scraper"