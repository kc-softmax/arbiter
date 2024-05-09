data "aws_route53_zone" "example_zone" {
  name         = var.zone_name
  private_zone = false

  depends_on = [var.example_elb]
}

resource "aws_route53_record" "example_record" {
  zone_id = data.aws_route53_zone.example_zone.zone_id
  name    = var.record_name
  type    = "A"

  alias {
    name                   = var.example_elb.dns_name
    zone_id                = var.example_elb.zone_id
    evaluate_target_health = true
  }
}
