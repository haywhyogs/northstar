variable "name" {
  description = "Globally unique, 5-50 letters and digits only."
  type        = string
}

variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "tags" {
  type = map(string)
}
