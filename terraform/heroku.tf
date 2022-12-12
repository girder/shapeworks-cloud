data "heroku_team" "heroku" {
  # This must be created by hand in the Heroku console
  name = "kitware"
}

module "django" {
  source  = "girder/django/heroku"
  version = "0.10.0"

  project_slug     = "shapeworks-cloud"
  route53_zone_id  = data.aws_route53_zone.shapeworks_cloud.zone_id
  heroku_team_name = data.heroku_team.heroku.name
  subdomain_name   = "app"

  heroku_postgresql_plan      = "hobby-basic"
  heroku_worker_dyno_quantity = 0

  ec2_worker_instance_type     = "m4.large"
  ec2_worker_instance_quantity = 1
  ec2_worker_ssh_public_key    = var.ec2_worker_ssh_public_key
  ec2_worker_volume_size       = 40

  additional_django_vars = {
    DJANGO_API_URL    = "https://www.shapeworks-cloud.org/api/v1"
  }
  django_cors_origin_whitelist = ["https://www.shapeworks-cloud.org"]
}

resource "aws_route53_record" "github_pages" {
  zone_id = data.aws_route53_zone.shapeworks_cloud.zone_id
  name    = "www"
  type    = "CNAME"
  ttl     = "300"
  records = ["girder.github.io."]
}
