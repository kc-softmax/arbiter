variable "cidr" {
    description = ""
    type = string
}
variable "region" {
    description = "specific deployment region"
    type = string
}
variable "instance_type" {
    description = "instance type(t3.medium, c5.large)"
    type = string
}
variable "zone_name" {
    description = "domain"
    type = string
}
variable "record_name" {
    description = "host"
    type = string
}