data "aws_route53_zone" "route53_zone" {
  name         = var.zone_name
  private_zone = false

  depends_on = [var.alb]
}

resource "aws_route53_record" "route53_record" {
  zone_id = data.aws_route53_zone.route53_zone.zone_id
  name    = var.record_name
  type    = "A"

  alias {
    name                   = var.alb.dns_name
    zone_id                = var.alb.zone_id
    evaluate_target_health = true
  }
}
